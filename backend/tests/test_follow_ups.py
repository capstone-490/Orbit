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
        "/api/v1/follow-ups",
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
        "/api/v1/follow-ups",
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
    assert mock_db.execute.call_count == 1


def test_list_follow_ups_is_scoped_to_current_advisor(mock_db, client):
    mock_db.fetchall.return_value = [
        {"id": 3, "advisor_id": 7, "client_id": 12, "status": "Pending"}
    ]

    response = client.get("/api/v1/follow-ups")

    assert response.status_code == 200
    assert response.json()[0]["advisor_id"] == 7
    query, params = mock_db.execute.call_args.args
    assert "WHERE advisor_id = %s" in query
    assert params == (7,)


def test_get_follow_up_hides_other_advisors(mock_db, client):
    mock_db.fetchone.return_value = None

    response = client.get("/api/v1/follow-ups/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Follow-up not found."


def test_update_status_is_scoped_and_persisted(mock_db, client):
    mock_db.fetchone.return_value = {
        "id": 3,
        "advisor_id": 7,
        "client_id": 12,
        "status": "Completed",
    }

    response = client.patch("/api/v1/follow-ups/3/status", json={"status": "Completed"})

    assert response.status_code == 200
    assert response.json()["status"] == "Completed"
    query, params = mock_db.execute.call_args.args
    assert "WHERE id = %(follow_up_id)s AND advisor_id = %(advisor_id)s" in query
    assert params["follow_up_id"] == 3
    assert params["advisor_id"] == 7


def test_update_discussion_notes_returns_saved_value(mock_db, client):
    mock_db.fetchone.return_value = {
        "id": 3,
        "advisor_id": 7,
        "client_id": 12,
        "discussion_notes": "Discussed next steps.",
    }

    response = client.patch(
        "/api/v1/follow-ups/3",
        json={"discussion_notes": " Discussed next steps. "},
    )

    assert response.status_code == 200
    assert response.json()["discussion_notes"] == "Discussed next steps."
    query, params = mock_db.execute.call_args.args
    assert "discussion_notes = %(discussion_notes)s" in query
    assert params["discussion_notes"] == "Discussed next steps."


def test_update_discussion_notes_accepts_empty_note(mock_db, client):
    mock_db.fetchone.return_value = {"id": 3, "discussion_notes": ""}

    response = client.patch("/api/v1/follow-ups/3", json={"discussion_notes": "   "})

    assert response.status_code == 200
    assert response.json()["discussion_notes"] == ""


def test_update_reason_strips_whitespace(mock_db, client):
    mock_db.fetchone.return_value = {"id": 3, "reason": "Updated reason"}

    response = client.patch("/api/v1/follow-ups/3", json={"reason": " Updated reason "})

    assert response.status_code == 200
    assert response.json()["reason"] == "Updated reason"
    assert mock_db.execute.call_args.args[1]["reason"] == "Updated reason"


@pytest.mark.parametrize(
    "payload",
    [{}],
)
def test_update_follow_up_rejects_empty_update_payload(mock_db, client, payload):
    response = client.patch("/api/v1/follow-ups/3", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "At least one field must be provided."
    mock_db.execute.assert_not_called()


def test_update_follow_up_rejects_client_id_change(mock_db, client):
    response = client.patch("/api/v1/follow-ups/3", json={"client_id": 12})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
    mock_db.execute.assert_not_called()


def test_update_follow_up_returns_not_found(mock_db, client):
    mock_db.fetchone.return_value = None

    response = client.patch(
        "/api/v1/follow-ups/3", json={"discussion_notes": "No record"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Follow-up not found."


@pytest.mark.parametrize("field", ["due_date", "priority", "status"])
def test_update_follow_up_rejects_null_non_nullable_fields(mock_db, client, field):
    response = client.patch("/api/v1/follow-ups/3", json={field: None})

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {
            "client_id": 1,
            "reason": " ",
            "financial_planning_stage": "Financial Plan",
            "due_date": "2026-12-01",
        },
        {
            "client_id": 1,
            "reason": "Valid",
            "financial_planning_stage": "Unknown",
            "due_date": "2026-12-01",
        },
        {
            "client_id": 1,
            "reason": "Valid",
            "financial_planning_stage": "Financial Plan",
            "due_date": "not-a-date",
        },
    ],
)
def test_create_follow_up_validates_input(mock_db, client, payload):
    response = client.post("/api/v1/follow-ups", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()
