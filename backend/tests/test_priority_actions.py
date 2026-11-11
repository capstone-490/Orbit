# Substantial AI assistance used; verified with backend unit tests.
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from psycopg import OperationalError

from app.api.v1.routers import priority_actions
from app.auth import get_current_advisor
from app.main import app
from app.services.ai_suggestions import get_suggestions
from app.services.priority_actions import rank_priority_actions

TODAY = date(2026, 11, 10)


def make_follow_up(id, days_from_today, priority="Medium", status="Pending"):
    return {
        "id": id,
        "client_id": 100 + id,
        "client_name": f"Client {id}",
        "reason": f"Follow-up {id}",
        "financial_planning_stage": "Financial Plan",
        "due_date": TODAY + timedelta(days=days_from_today),
        "priority": priority,
        "status": status,
    }


# --------------------------------------------------------------------------
# Ranking rules (pure function, no database)
# --------------------------------------------------------------------------


def test_ranking_orders_overdue_then_due_soon_then_high_priority():
    follow_ups = [
        make_follow_up(1, 6, priority="High"),  # high priority, later
        make_follow_up(2, 1),  # due tomorrow
        make_follow_up(3, -2),  # overdue
    ]

    ranked = rank_priority_actions(follow_ups, TODAY)

    assert [a["follow_up_id"] for a in ranked] == [3, 2, 1]
    assert [a["urgency"] for a in ranked] == ["overdue", "due_soon", "high_priority"]


def test_ranking_excludes_completed_cancelled_and_non_urgent():
    follow_ups = [
        make_follow_up(1, -3, status="Completed"),
        make_follow_up(2, -3, status="Cancelled"),
        make_follow_up(3, 5, priority="Medium"),  # not due soon, not High
        make_follow_up(4, 8, priority="High"),  # outside the 7-day window
        make_follow_up(5, 0, status="In Progress"),  # active and due today
    ]

    ranked = rank_priority_actions(follow_ups, TODAY)

    assert [a["follow_up_id"] for a in ranked] == [5]


def test_ranking_boundaries():
    follow_ups = [
        make_follow_up(1, 2),  # last day of "due soon"
        make_follow_up(2, 3),  # first day after "due soon", Medium -> excluded
        make_follow_up(3, 7, priority="High"),  # last day of High window
    ]

    ranked = rank_priority_actions(follow_ups, TODAY)

    assert {a["follow_up_id"]: a["urgency"] for a in ranked} == {
        1: "due_soon",
        3: "high_priority",
    }


def test_ranking_within_same_urgency_uses_priority_then_due_date():
    follow_ups = [
        make_follow_up(1, -1, priority="Low"),
        make_follow_up(2, -5, priority="Medium"),
        make_follow_up(3, -1, priority="High"),
        make_follow_up(4, -3, priority="Medium"),
    ]

    ranked = rank_priority_actions(follow_ups, TODAY)

    # High first; among Medium, the most overdue (earliest due date) first.
    assert [a["follow_up_id"] for a in ranked] == [3, 2, 4, 1]


@pytest.mark.parametrize(
    ("days", "priority", "expected"),
    [
        (-1, "Medium", "Overdue by 1 day"),
        (-4, "Medium", "Overdue by 4 days"),
        (0, "Medium", "Due today"),
        (1, "Medium", "Due tomorrow"),
        (2, "Medium", "Due in 2 days"),
        (5, "High", "High priority, due in 5 days"),
    ],
)
def test_ranking_explains_each_item(days, priority, expected):
    ranked = rank_priority_actions([make_follow_up(1, days, priority)], TODAY)

    assert ranked[0]["urgency_reason"] == expected


# --------------------------------------------------------------------------
# AI suggestion service
# --------------------------------------------------------------------------


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result or []
        self.error = error
        self.received = None

    def suggest(self, items):
        self.received = items
        if self.error:
            raise self.error
        return self.result


def ranked_sample():
    return rank_priority_actions([make_follow_up(1, -1), make_follow_up(2, 0)], TODAY)


def test_suggestions_disabled_without_provider():
    assert get_suggestions(ranked_sample(), None) == {
        "status": "disabled",
        "suggestions": [],
    }


def test_suggestions_unavailable_when_provider_fails():
    provider = FakeProvider(error=TimeoutError("AI timed out"))

    assert get_suggestions(ranked_sample(), provider) == {
        "status": "unavailable",
        "suggestions": [],
    }


def test_suggestions_drop_unknown_ids_and_blank_text():
    provider = FakeProvider(
        result=[
            {"follow_up_id": 1, "text": "  Call the client today.  "},
            {"follow_up_id": 999, "text": "Not one of this advisor's items."},
            {"follow_up_id": 2, "text": "   "},
            "not a dict",
        ]
    )

    result = get_suggestions(ranked_sample(), provider)

    assert result == {
        "status": "available",
        "suggestions": [{"follow_up_id": 1, "text": "Call the client today."}],
    }


def test_suggestions_do_not_send_client_identity_to_ai():
    provider = FakeProvider()

    get_suggestions(ranked_sample(), provider)

    sent = provider.received[0]
    assert "client_name" not in sent
    assert "client_id" not in sent
    assert set(sent) == {
        "follow_up_id",
        "reason",
        "financial_planning_stage",
        "priority",
        "urgency",
    }


def test_suggestions_skip_ai_when_nothing_is_urgent():
    provider = FakeProvider(error=AssertionError("should not be called"))

    assert get_suggestions([], provider) == {"status": "available", "suggestions": []}


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(priority_actions, "get_connection", lambda: conn)
    monkeypatch.setattr(priority_actions, "_today", lambda: TODAY)
    monkeypatch.setattr(priority_actions, "get_ai_provider", lambda: None)
    app.dependency_overrides[get_current_advisor] = lambda: {"id": 7}
    yield cursor
    app.dependency_overrides.pop(get_current_advisor, None)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_priority_actions_requires_authentication(client):
    response = client.get("/priority-actions")

    assert response.status_code == 401


def test_priority_actions_are_scoped_to_current_advisor(mock_db, client):
    mock_db.fetchall.return_value = []

    response = client.get("/priority-actions")

    assert response.status_code == 200
    query, params = mock_db.execute.call_args.args
    assert "WHERE f.advisor_id = %s" in query
    assert "c.advisor_id = f.advisor_id" in query
    assert params[0] == 7
    assert params[2] == TODAY + timedelta(days=7)


def test_priority_actions_returns_ranked_items_and_total(mock_db, client):
    mock_db.fetchall.return_value = [
        make_follow_up(1, 1),
        make_follow_up(2, -3),
        make_follow_up(3, 4, priority="High"),
    ]

    response = client.get("/priority-actions", params={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["follow_up_id"] for item in body["items"]] == [2, 1]
    assert body["items"][0]["urgency"] == "overdue"
    assert body["items"][0]["urgency_reason"] == "Overdue by 3 days"
    assert body["items"][0]["client_name"] == "Client 2"


@pytest.mark.parametrize("limit", [0, 51, "abc"])
def test_priority_actions_rejects_invalid_limit(mock_db, client, limit):
    response = client.get("/priority-actions", params={"limit": limit})

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


def test_priority_actions_database_error_returns_500(mock_db, client):
    mock_db.execute.side_effect = OperationalError("database down")

    response = client.get("/priority-actions")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to retrieve priority actions."


def test_suggestions_endpoint_reports_disabled(mock_db, client):
    mock_db.fetchall.return_value = [make_follow_up(1, -1)]

    response = client.get("/priority-actions/suggestions")

    assert response.status_code == 200
    assert response.json() == {"status": "disabled", "suggestions": []}


def test_suggestions_endpoint_survives_ai_failure(mock_db, client, monkeypatch):
    mock_db.fetchall.return_value = [make_follow_up(1, -1)]
    monkeypatch.setattr(
        priority_actions,
        "get_ai_provider",
        lambda: FakeProvider(error=RuntimeError("AI service down")),
    )

    response = client.get("/priority-actions/suggestions")

    assert response.status_code == 200
    assert response.json() == {"status": "unavailable", "suggestions": []}


def test_suggestions_endpoint_returns_ai_suggestions(mock_db, client, monkeypatch):
    mock_db.fetchall.return_value = [make_follow_up(1, -1)]
    monkeypatch.setattr(
        priority_actions,
        "get_ai_provider",
        lambda: FakeProvider(result=[{"follow_up_id": 1, "text": "Call today."}]),
    )

    response = client.get("/priority-actions/suggestions")

    assert response.status_code == 200
    assert response.json() == {
        "status": "available",
        "suggestions": [{"follow_up_id": 1, "text": "Call today."}],
    }


def test_suggestions_endpoint_requires_authentication(client):
    response = client.get("/priority-actions/suggestions")

    assert response.status_code == 401