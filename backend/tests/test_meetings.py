from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.routers import meetings
from app.main import app

client = TestClient(app)


def CreateMeeting(advisor_id, client_id, meeting_date, completion_status):
    return {
        "id": 1,
        "advisor_id": advisor_id,
        "client_id": client_id,
        "meeting_date": meeting_date,
        "completion_status": completion_status,
    }


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setattr(meetings, "get_connection", lambda: conn)

    return cursor


def test_list_meetings_empty(mock_db):
    mock_db.fetchall.return_value = []

    response = client.get("/meetings/1")

    assert response.status_code == 200
    assert response.json() == []

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "SELECT id, client_id, advisor_id, meeting_date, completion_status" in query
    assert params["advisor_id"] == 1


def test_list_meetings_with_data(mock_db):
    mock_db.fetchall.return_value = [
        (1, 1, 1, "2024-06-01T10:00:00Z", "Scheduled"),
        (2, 2, 1, "2024-06-02T11:00:00Z", "Completed"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]

    response = client.get("/meetings/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "client_id": 1,
            "advisor_id": 1,
            "meeting_date": "2024-06-01T10:00:00Z",
            "completion_status": "Scheduled",
        },
        {
            "id": 2,
            "client_id": 2,
            "advisor_id": 1,
            "meeting_date": "2024-06-02T11:00:00Z",
            "completion_status": "Completed",
        },
    ]

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "SELECT id, client_id, advisor_id, meeting_date, completion_status" in query
    assert params["advisor_id"] == 1


def test_list_scheduled_meetings(mock_db):
    mock_db.fetchall.return_value = [
        (1, 1, 1, "2024-06-01T10:00:00Z", "Scheduled"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]

    response = client.get("/meetings/scheduled/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "client_id": 1,
            "advisor_id": 1,
            "meeting_date": "2024-06-01T10:00:00Z",
            "completion_status": "Scheduled",
        }
    ]

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "SELECT id, client_id, advisor_id, meeting_date, completion_status" in query
    assert params["advisor_id"] == 1


def test_list_completed_meetings(mock_db):
    mock_db.fetchall.return_value = [
        (2, 2, 1, "2024-06-02T11:00:00Z", "Completed"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]

    response = client.get("/meetings/completed/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 2,
            "client_id": 2,
            "advisor_id": 1,
            "meeting_date": "2024-06-02T11:00:00Z",
            "completion_status": "Completed",
        }
    ]

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "SELECT id, client_id, advisor_id, meeting_date, completion_status" in query
    assert params["advisor_id"] == 1


def test_list_meetings_for_client(mock_db):
    mock_db.fetchall.return_value = [
        (1, 1, 1, "2024-06-01T10:00:00Z", "Scheduled"),
        (2, 1, 2, "2024-06-02T11:00:00Z", "Completed"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]

    response = client.get("/meetings/1/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "client_id": 1,
            "advisor_id": 1,
            "meeting_date": "2024-06-01T10:00:00Z",
            "completion_status": "Scheduled",
        },
        {
            "id": 2,
            "client_id": 1,
            "advisor_id": 2,
            "meeting_date": "2024-06-02T11:00:00Z",
            "completion_status": "Completed",
        },
    ]

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "SELECT id, client_id, advisor_id, meeting_date, completion_status" in query
    assert params["advisor_id"] == 1
    assert params["client_id"] == 1
