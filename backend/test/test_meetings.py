<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
from types import SimpleNamespace
=======
from datetime import UTC
>>>>>>> 610e8c5 (adding http rest api tests and testing if signing is working)
=======
>>>>>>> 0b70d36 (used ruff to fix formatting issues)
=======
from types import SimpleNamespace
>>>>>>> 6bf19b5 (finished adding tests for meetings)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
<<<<<<< HEAD
<<<<<<< HEAD

from app.main import app
from app.routers import meetings

client = TestClient(app)


def CreateMeeting(advisor_id, client_id, meeting_date, completion_status):
    return {
        "id": 1,
        "advisor_id": advisor_id,
        "client_id": client_id,
        "meeting_date": meeting_date,
        "completion_status": completion_status,
    }

=======
from psycopg.errors import UniqueViolation

import main
from main import ClientCreate
=======
>>>>>>> 0b70d36 (used ruff to fix formatting issues)

from app.main import app
from app.routers import meetings

<<<<<<< HEAD
client = TestClient(main.app)
>>>>>>> 610e8c5 (adding http rest api tests and testing if signing is working)
=======
client = TestClient(app)
>>>>>>> 1aef9be (fixed small issue)


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

<<<<<<< HEAD
<<<<<<< HEAD
    monkeypatch.setattr(meetings, "get_connection", lambda: conn)
=======
    monkeypatch.setattr(main, "get_connection", lambda: conn)
>>>>>>> 610e8c5 (adding http rest api tests and testing if signing is working)
=======
    monkeypatch.setattr(meetings, "get_connection", lambda: conn)
>>>>>>> 6bf19b5 (finished adding tests for meetings)

    return cursor


def test_list_meetings_empty(mock_db):
    mock_db.fetchall.return_value = []
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
    mock_db.description = [MagicMock(name="id"), MagicMock(name="client_id"), MagicMock(name="advisor_id"), MagicMock(name="meeting_date"), MagicMock(name="completion_status")]
>>>>>>> 610e8c5 (adding http rest api tests and testing if signing is working)
=======
    mock_db.description = [
        MagicMock(name="id"),
        MagicMock(name="client_id"),
        MagicMock(name="advisor_id"),
        MagicMock(name="meeting_date"),
        MagicMock(name="completion_status"),
    ]
>>>>>>> e3e9a9c (changed formatting using ruff and moved things around)
=======
>>>>>>> 6bf19b5 (finished adding tests for meetings)

    response = client.get("/meetings/1")

    assert response.status_code == 200
    assert response.json() == []

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 6bf19b5 (finished adding tests for meetings)
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

<<<<<<< HEAD
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
=======
    mock_db.execute.assert_called_once_with(
        """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s
                ORDER BY meeting_date DESC, id DESC
                """,
        (1,),
    )
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> 610e8c5 (adding http rest api tests and testing if signing is working)
=======

>>>>>>> 2bd0cf2 (testing commit verification)
=======
>>>>>>> 327a269 (reverting last change)
=======
    assert (
        "SELECT id, client_id, advisor_id, meeting_date, completion_status"
        in query
    )
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

    assert (
        "SELECT id, client_id, advisor_id, meeting_date, completion_status"
        in query
    )
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

    assert (
        "SELECT id, client_id, advisor_id, meeting_date, completion_status"
        in query
    )
    assert params["advisor_id"] == 1
    assert params["client_id"] == 1
>>>>>>> 6bf19b5 (finished adding tests for meetings)
