# Substantial AI assistance used; verified with backend tests and live auth smoke test.
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routers import meetings
from app.auth import create_access_token
from app.main import app

client = TestClient(
    app,
    headers={"Authorization": f"Bearer {create_access_token(1)}"},
)


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

    response = client.get("/api/v1/meetings/1")

    assert response.status_code == 200
    assert response.json() == []

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "FROM t_meetings m" in query
    assert "JOIN t_clients c ON c.id = m.client_id" in query
    assert "m.duration_minutes" in query
    assert "c.name AS client_name" in query
    assert params["advisor_id"] == 1


def test_create_continuing_session_for_existing_client(mock_db):
    mock_db.fetchone.side_effect = [
        (7,),
        None,
        (11, 7, 1, "2026-12-01T10:00:00Z", "Scheduled"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]

    response = client.post(
        "/api/v1/meetings/continuing-session",
        json={"client_id": 7, "meeting_date": "2026-12-01T10:00:00Z"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 11,
        "client_id": 7,
        "advisor_id": 1,
        "meeting_date": "2026-12-01T10:00:00Z",
        "completion_status": "Scheduled",
    }
    assert mock_db.execute.call_count == 4
    insert_query, insert_params = mock_db.execute.call_args.args
    assert "INSERT INTO t_meetings" in insert_query
    assert insert_params["advisor_id"] == 1
    assert insert_params["client_id"] == 7


def test_continuing_session_requires_client_belonging_to_advisor(mock_db):
    mock_db.fetchone.return_value = None

    response = client.post(
        "/api/v1/meetings/continuing-session",
        json={"client_id": 7, "meeting_date": "2026-12-01T10:00:00Z"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."
    assert mock_db.execute.call_count == 2


def test_continuing_session_rejects_unavailable_time_slot(mock_db):
    mock_db.fetchone.side_effect = [
        (7,),
        None,
        (11, 7, 1, "2026-12-01T10:00:00Z", "Scheduled"),
        (7,),
        (11,),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="completion_status"),
    ]
    request = {
        "client_id": 7,
        "meeting_date": "2026-12-01T10:00:00Z",
    }

    first_response = client.post("/api/v1/meetings/continuing-session", json=request)
    second_response = client.post("/api/v1/meetings/continuing-session", json=request)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Time slot is unavailable."
    assert mock_db.execute.call_count == 7


def test_continuing_session_rejects_overlapping_one_hour_meeting(mock_db):
    mock_db.fetchone.side_effect = [(7,), (11,)]

    response = client.post(
        "/api/v1/meetings/continuing-session",
        json={"client_id": 7, "meeting_date": "2026-11-07T10:30:00Z"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Time slot is unavailable."
    availability_query, params = mock_db.execute.call_args_list[2].args
    assert "meeting_date < %(meeting_end)s" in availability_query
    assert "meeting_date + %(duration)s > %(meeting_date)s" in availability_query
    assert params["meeting_end"].isoformat() == "2026-11-07T11:30:00+00:00"
    assert params["duration"] == timedelta(hours=1)


def test_continuing_session_requires_timezone(mock_db):
    response = client.post(
        "/api/v1/meetings/continuing-session",
        json={"client_id": 7, "meeting_date": "2026-12-01T10:00:00"},
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


def test_cannot_read_another_advisors_meetings(mock_db):
    response = client.get("/api/v1/meetings/2")

    assert response.status_code == 403
    mock_db.execute.assert_not_called()


def test_list_meetings_with_data(mock_db):
    mock_db.fetchall.return_value = [
        (1, 1, 1, "2024-06-01T10:00:00Z", 30, "Scheduled", "Sarah Smith"),
        (2, 2, 1, "2024-06-02T11:00:00Z", 45, "Completed", "John Doe"),
    ]
    mock_db.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="client_id"),
        SimpleNamespace(name="advisor_id"),
        SimpleNamespace(name="meeting_date"),
        SimpleNamespace(name="duration_minutes"),
        SimpleNamespace(name="completion_status"),
        SimpleNamespace(name="client_name"),
    ]

    response = client.get("/api/v1/meetings/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "client_id": 1,
            "advisor_id": 1,
            "meeting_date": "2024-06-01T10:00:00Z",
            "duration_minutes": 30,
            "completion_status": "Scheduled",
            "client_name": "Sarah Smith",
        },
        {
            "id": 2,
            "client_id": 2,
            "advisor_id": 1,
            "meeting_date": "2024-06-02T11:00:00Z",
            "duration_minutes": 45,
            "completion_status": "Completed",
            "client_name": "John Doe",
        },
    ]

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "FROM t_meetings m" in query
    assert "JOIN t_clients c ON c.id = m.client_id" in query
    assert "m.duration_minutes" in query
    assert "c.name AS client_name" in query
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

    response = client.get("/api/v1/meetings/scheduled/1")

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

    response = client.get("/api/v1/meetings/completed/1")

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

    response = client.get("/api/v1/meetings/1/1")

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


RESCHEDULE_URL = "/api/v1/meetings/1/reschedule"
FUTURE_START = "2030-06-01T10:00:00+00:00"


def mock_reschedule_queries(cursor, meeting, conflict=None):
    """Mock advisory lock, meeting lookup, conflict check, and update."""
    updated = (
        meeting[0],
        meeting[1],
        meeting[2],
        datetime.fromisoformat(FUTURE_START),
        meeting[4],
        meeting[5],
    )

    cursor.fetchone.side_effect = [
        meeting,
        conflict,
        updated,
    ]


def test_reschedule_meeting_success(mock_db):
    meeting = (
        1,  # meeting ID
        2,  # client ID
        1,  # advisor ID
        datetime(2030, 5, 30, 10, tzinfo=UTC),
        30,  # duration
        "Scheduled",
    )
    mock_reschedule_queries(mock_db, meeting)

    response = client.patch(
        RESCHEDULE_URL,
        json={"new_start": FUTURE_START},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["client_id"] == 2
    assert data["advisor_id"] == 1
    assert data["duration_minutes"] == 30
    assert data["notification_status"] == "not_implemented"

    assert mock_db.execute.call_count == 4
    update_query = mock_db.execute.call_args_list[-1].args[0]
    assert "UPDATE t_meetings" in update_query


def test_reschedule_meeting_conflict(mock_db):
    meeting = (
        1,
        2,
        1,
        datetime(2030, 5, 30, 10, tzinfo=UTC),
        30,
        "Scheduled",
    )
    mock_db.fetchone.side_effect = [
        meeting,
        (99,),  # Conflicting meeting ID
    ]

    response = client.patch(
        RESCHEDULE_URL,
        json={"new_start": FUTURE_START},
    )

    assert response.status_code == 409
    assert "conflicts" in response.json()["detail"]
    assert mock_db.execute.call_count == 3


def test_reschedule_completed_meeting(mock_db):
    mock_db.fetchone.return_value = (
        1,
        2,
        1,
        datetime(2030, 5, 30, 10, tzinfo=UTC),
        30,
        "Completed",
    )

    response = client.patch(
        RESCHEDULE_URL,
        json={"new_start": FUTURE_START},
    )

    assert response.status_code == 409
    assert mock_db.execute.call_count == 2


def test_reschedule_meeting_not_found(mock_db):
    mock_db.fetchone.return_value = None

    response = client.patch(
        RESCHEDULE_URL,
        json={"new_start": FUTURE_START},
    )

    assert response.status_code == 404
    assert mock_db.execute.call_count == 2


@pytest.mark.parametrize(
    "invalid_start",
    [
        "2020-01-01T10:00:00+00:00",
        "2030-06-01T10:00:00",
        "not-a-date",
    ],
)
def test_reschedule_invalid_date(mock_db, invalid_start):
    response = client.patch(
        RESCHEDULE_URL,
        json={"new_start": invalid_start},
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


def test_reschedule_requires_authentication(mock_db):
    unauthenticated_client = TestClient(app)

    response = unauthenticated_client.patch(
        RESCHEDULE_URL,
        json={"new_start": FUTURE_START},
    )

    assert response.status_code == 401
    mock_db.execute.assert_not_called()
