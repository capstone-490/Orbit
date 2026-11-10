from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routers import follow_ups
from app.auth import get_current_advisor
from app.main import app


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(follow_ups, "get_connection", lambda: conn)
    app.dependency_overrides[get_current_advisor] = lambda: {"id": 7}
    yield cursor
    app.dependency_overrides.pop(get_current_advisor, None)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_create_follow_up_requires_assigned_client(mock_db, client):
    mock_db.fetchone.return_value = None

    response = client.post(
        "/follow-ups",
        json={
            "client_id": 12,
            "reason": "Review investment proposal",
            "financial_planning_stage": "Financial Plan",
            "due_date": "2026-12-01",
        },
    )

    assert response.status_code == 404
    assert "not assigned" in response.json()["detail"]
    mock_db.execute.assert_called_once()


def test_create_follow_up_returns_record(mock_db, client):
    mock_db.fetchone.side_effect = [
        (1,),
        {
            "id": 3,
            "advisor_id": 7,
            "client_id": 12,
            "reason": "Review investment proposal",
            "financial_planning_stage": "Financial Plan",
            "due_date": "2026-12-01",
            "priority": "High",
            "status": "Pending",
        },
    ]

    response = client.post(
        "/follow-ups",
        json={
            "client_id": 12,
            "reason": "Review investment proposal",
            "financial_planning_stage": "Financial Plan",
            "due_date": "2026-12-01",
            "priority": "High",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 3
    assert response.json()["priority"] == "High"
    assert mock_db.execute.call_count == 2


def test_list_follow_ups_is_scoped_to_current_advisor(mock_db, client):
    mock_db.fetchall.return_value = [
        {"id": 3, "advisor_id": 7, "client_id": 12, "status": "Pending"}
    ]

    response = client.get("/follow-ups")

    assert response.status_code == 200
    assert response.json()[0]["advisor_id"] == 7
    query, params = mock_db.execute.call_args.args
    assert "WHERE advisor_id = %s" in query
    assert params == (7,)


def test_get_follow_up_hides_other_advisors(mock_db, client):
    mock_db.fetchone.return_value = None

    response = client.get("/follow-ups/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Follow-up not found."


def test_update_status_is_scoped_and_persisted(mock_db, client):
    mock_db.fetchone.return_value = {
        "id": 3,
        "advisor_id": 7,
        "client_id": 12,
        "status": "Completed",
    }

    response = client.patch("/follow-ups/3/status", json={"status": "Completed"})

    assert response.status_code == 200
    assert response.json()["status"] == "Completed"
    query, params = mock_db.execute.call_args.args
    assert "WHERE id = %(follow_up_id)s AND advisor_id = %(advisor_id)s" in query
    assert params["follow_up_id"] == 3
    assert params["advisor_id"] == 7


@pytest.mark.parametrize(
    "payload",
    [
        {"client_id": 1, "reason": " ", "financial_planning_stage": "Financial Plan", "due_date": "2026-12-01"},
        {"client_id": 1, "reason": "Valid", "financial_planning_stage": "Unknown", "due_date": "2026-12-01"},
        {"client_id": 1, "reason": "Valid", "financial_planning_stage": "Financial Plan", "due_date": "not-a-date"},
    ],
)
def test_create_follow_up_validates_input(mock_db, client, payload):
    response = client.post("/follow-ups", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()
