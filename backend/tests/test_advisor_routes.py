from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from psycopg import OperationalError
from psycopg.rows import dict_row

from app.api.v1.routers import advisors
from app.auth import get_current_advisor
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated_advisor():
    previous_override = app.dependency_overrides.get(get_current_advisor)
    app.dependency_overrides[get_current_advisor] = lambda: {"id": 2}
    yield
    if previous_override is None:
        app.dependency_overrides.pop(get_current_advisor, None)
    else:
        app.dependency_overrides[get_current_advisor] = previous_override


@pytest.fixture
def mock_db(monkeypatch):
    connection = MagicMock()
    cursor = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(advisors, "get_connection", lambda: connection)
    return connection, cursor


def test_list_advisor_tasks_returns_client_names(mock_db):
    _, cursor = mock_db
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "advisorId": 2,
            "taskTitle": "Call client",
            "dueDate": "2026-10-28",
            "status": "TO_DO",
            "createdAt": "2026-10-28T10:00:00",
            "clientId": 10,
            "clientName": "Sarah Smith",
        }
    ]

    response = client.get("/advisors/2/tasks")

    assert response.status_code == 200
    assert response.json()[0]["clientName"] == "Sarah Smith"
    assert response.json()[0]["status"] == "TO_DO"
    assert "tag" not in response.json()[0]
    query, params = cursor.execute.call_args.args
    assert "LEFT JOIN clients" in query
    assert "t.tag" not in query
    assert params == (2,)


def test_create_advisor_task_returns_created_task(mock_db):
    connection, cursor = mock_db
    cursor.fetchone.return_value = {
        "id": 8,
        "advisorId": 2,
        "taskTitle": "Review portfolio",
        "dueDate": "2026-11-20",
        "status": "TO_DO",
        "clientId": 10,
        "clientName": "Sarah Smith",
    }

    response = client.post(
        "/advisors/2/tasks",
        json={
            "taskTitle": " Review portfolio ",
            "dueDate": "2026-11-20",
            "clientId": 10,
        },
    )

    assert response.status_code == 201
    assert response.json()["taskTitle"] == "Review portfolio"
    assert response.json()["clientName"] == "Sarah Smith"
    query, params = cursor.execute.call_args.args
    assert "INSERT INTO tasks" in query
    assert "advisor_id = %s" in query
    assert params == (2, 10, "Review portfolio", date(2026, 11, 20), 10, 10, 2)
    connection.commit.assert_called_once()


def test_create_advisor_task_rejects_another_advisors_client(mock_db):
    _, cursor = mock_db
    cursor.fetchone.return_value = None

    response = client.post(
        "/advisors/2/tasks",
        json={
            "taskTitle": "Review portfolio",
            "dueDate": "2026-11-20",
            "clientId": 10,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Client not found for advisor"}


def test_create_advisor_task_rejects_a_mismatched_advisor():
    response = client.post(
        "/advisors/1/tasks",
        json={"taskTitle": "Review portfolio", "dueDate": "2026-11-20"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"taskTitle": "   ", "dueDate": "2026-11-20"},
        {"taskTitle": "Missing due date"},
        {"taskTitle": "Invalid due date", "dueDate": "not-a-date"},
    ],
)
def test_create_advisor_task_validates_required_fields(mock_db, payload):
    _, cursor = mock_db

    response = client.post("/advisors/2/tasks", json=payload)

    assert response.status_code == 422
    cursor.execute.assert_not_called()


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
            "completionStatus": "Scheduled",
            "locationOrPlatform": "Zoom",
        }
    ]

    response = client.get("/advisors/2/schedule")

    assert response.status_code == 200
    assert response.json()[0]["time"] == "2026-10-28T14:00:00"
    assert response.json()[0]["completionStatus"] == "Scheduled"
    assert "statusText" not in response.json()[0]
    assert "actionButtonLabel" not in response.json()[0]
    query, params = cursor.execute.call_args.args
    assert "JOIN clients" in query
    assert "completion_status" in query
    assert "status_text" not in query
    assert "action_button_label" not in query
    assert params == (2,)


def test_list_advisor_clients_returns_rows(mock_db):
    connection, cursor = mock_db
    cursor.fetchall.return_value = [
        {
            "id": 10,
            "name": "Sarah Smith",
            "age": 42,
            "createdAt": "2026-10-28T17:57:27+00:00",
        }
    ]

    response = client.get("/advisors/2/clients")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 10,
            "name": "Sarah Smith",
            "age": 42,
            "createdAt": "2026-10-28T17:57:27+00:00",
        }
    ]
    query, params = cursor.execute.call_args.args
    assert "WHERE advisor_id = %s" in query
    assert "age" in query
    assert "date_of_birth" not in query
    assert params == (2,)
    assert connection.cursor.call_args.kwargs == {"row_factory": dict_row}


def test_update_task_status_persists_and_returns_updated_task(mock_db):
    connection, cursor = mock_db
    cursor.fetchone.return_value = {"id": 1, "status": "IN_PROGRESS"}

    response = client.patch("/advisors/tasks/1", json={"status": "IN_PROGRESS"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "status": "IN_PROGRESS"}
    query, params = cursor.execute.call_args.args
    assert "UPDATE tasks" in query
    assert "SET status = %s" in query
    assert params == ("IN_PROGRESS", 1)
    connection.commit.assert_called_once()


def test_update_task_status_returns_404_for_missing_task(mock_db):
    _, cursor = mock_db
    cursor.fetchone.return_value = None

    response = client.patch("/advisors/tasks/999", json={"status": "COMPLETED"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.parametrize("status", ["TO_DO", "IN_PROGRESS", "IN_REVIEW", "COMPLETED"])
def test_update_task_status_accepts_supported_values(mock_db, status):
    _, cursor = mock_db
    cursor.fetchone.return_value = {"id": 1, "status": status}

    response = client.patch("/advisors/tasks/1", json={"status": status})

    assert response.status_code == 200
    assert response.json()["status"] == status


def test_update_task_status_rejects_unsupported_value():
    response = client.patch("/advisors/tasks/1", json={"status": "BLOCKED"})

    assert response.status_code == 422


def test_update_task_status_reports_database_errors(mock_db):
    _, cursor = mock_db
    cursor.execute.side_effect = OperationalError("database unavailable")

    response = client.patch("/advisors/tasks/1", json={"status": "TO_DO"})

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
    cursor.execute.side_effect = OperationalError("database unavailable")

    response = getattr(client, method)(path)

    assert response.status_code == 500
