from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import advisor

client = TestClient(app)


@pytest.fixture
def mock_db(monkeypatch):
    connection = MagicMock()
    cursor = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(advisor, "get_connection", lambda: connection)
    return connection, cursor


def test_list_advisor_tasks_returns_client_names(mock_db):
    _, cursor = mock_db
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "advisorId": 2,
            "taskTitle": "Call client",
            "dueDate": "2026-10-28",
            "tag": "TODAY",
            "completed": False,
            "createdAt": "2026-10-28T10:00:00",
            "clientId": 10,
            "clientName": "Sarah Smith",
        }
    ]

    response = client.get("/advisors/2/tasks")

    assert response.status_code == 200
    assert response.json()[0]["clientName"] == "Sarah Smith"
    assert response.json()[0]["completed"] is False
    query, params = cursor.execute.call_args.args
    assert "LEFT JOIN clients" in query
    assert params == (2,)


def test_list_advisor_schedule_returns_dict_rows(mock_db):
    _, cursor = mock_db
    cursor.fetchall.return_value = [
        {
            "id": 3,
            "time": "2026-10-28T14:00:00",
            "duration": "30 mins",
            "clientName": "Sarah Smith",
            "clientId": 10,
            "category": "Review",
            "agenda": "Review account",
            "statusText": "Confirmed",
            "locationOrPlatform": "Zoom",
            "actionButtonLabel": "Join",
        }
    ]

    response = client.get("/advisors/2/schedule")

    assert response.status_code == 200
    assert response.json()[0]["time"] == "2026-10-28T14:00:00"
    assert response.json()[0]["actionButtonLabel"] == "Join"
    query, params = cursor.execute.call_args.args
    assert "JOIN clients" in query
    assert params == (2,)


def test_list_advisor_clients_returns_rows(mock_db):
    _, cursor = mock_db
    cursor.fetchall.return_value = [{"id": 10, "name": "Sarah Smith"}]

    response = client.get("/advisors/2/clients")

    assert response.status_code == 200
    assert response.json() == [{"id": 10, "name": "Sarah Smith"}]
    query, params = cursor.execute.call_args.args
    assert "WHERE advisor_id = %s" in query
    assert params == (2,)


def test_update_task_completion_persists_and_returns_updated_task(mock_db):
    connection, cursor = mock_db
    cursor.fetchone.return_value = {"id": 1, "completed": True}

    response = client.patch("/advisors/tasks/1", json={"completed": True})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "completed": True}
    query, params = cursor.execute.call_args.args
    assert "UPDATE tasks" in query
    assert params == (True, 1)
    connection.commit.assert_called_once()


def test_update_task_completion_returns_404_for_missing_task(mock_db):
    _, cursor = mock_db
    cursor.fetchone.return_value = None

    response = client.patch("/advisors/tasks/999", json={"completed": True})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_update_task_completion_requires_boolean(mock_db):
    response = client.patch("/advisors/tasks/1", json={"completed": "yes"})

    assert response.status_code == 422


def test_update_task_completion_reports_database_errors(mock_db):
    _, cursor = mock_db
    cursor.execute.side_effect = RuntimeError("database unavailable")

    response = client.patch("/advisors/tasks/1", json={"completed": True})

    assert response.status_code == 500
    assert response.json() == {"detail": "database unavailable"}


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/advisors/1/tasks", "get"),
        ("/advisors/1/schedule", "get"),
        ("/advisors/1/clients", "get"),
    ],
)
def test_advisor_routes_report_database_errors(mock_db, path, method):
    _, cursor = mock_db
    cursor.execute.side_effect = RuntimeError("database unavailable")

    response = getattr(client, method)(path)

    assert response.status_code == 500
