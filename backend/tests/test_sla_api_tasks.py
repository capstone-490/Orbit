# Below 50% AI-generated
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from psycopg import Error as PsycopgError

from app.api.v1.routers.tasks import build_task_response
from app.services.sla_cal import UrgencyState, compute_urgency


@pytest.fixture
def mock_task_row():
    return (
        1,
        "Follow up with customer",
        "Contact customer regarding renewal",
        10,
        "Todo",
        datetime(2026, 11, 5, 12, 0, tzinfo=UTC),
        datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def mock_db():
    with patch("app.api.v1.routers.tasks.get_connection") as mock_conn:
        connection = MagicMock()

        mock_conn.return_value.__enter__.return_value = connection

        yield connection


def test_get_tasks_success(client, mock_db, mock_task_row):

    mock_db.execute.return_value.fetchall.return_value = [mock_task_row]

    response = client.get("/tasks", params={"client_id": 10, "user_timezone": "UTC"})

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["title"] == "Follow up with customer"
    assert data[0]["client_id"] == 10
    assert data[0]["status"] == "Todo"


def test_get_tasks_empty(client, mock_db):

    mock_db.execute.return_value.fetchall.return_value = []

    response = client.get("/tasks", params={"client_id": 10})

    assert response.status_code == 200
    assert response.json() == []


def test_get_tasks_invalid_timezone(client, mock_db):

    response = client.get(
        "/tasks",
        params={"client_id": 10, "user_timezone": "Invalid/Timezone"},
    )

    assert response.status_code == 400


def test_get_tasks_database_error(client, mock_db):

    mock_db.execute.side_effect = PsycopgError("Database error")

    response = client.get("/tasks", params={"client_id": 10})

    assert response.status_code == 500
    assert response.json()["detail"] == "Database operation failed"


@pytest.fixture
def valid_task_payload():

    return {
        "title": "Follow up with customer",
        "description": "Contact customer regarding renewal",
        "client_id": 10,
        "status": "Todo",
        "due_date": "2026-11-05T12:00:00+00:00",
        "last_contact_date": "2026-10-25T12:00:00+00:00",
    }


def test_create_task_success(client, mock_db, mock_task_row, valid_task_payload):

    mock_db.execute.return_value.fetchone.return_value = mock_task_row

    response = client.post(
        "/tasks", params={"user_timezone": "UTC"}, json=valid_task_payload
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Follow up with customer"
    assert data["client_id"] == 10
    assert data["status"] == "Todo"


def test_create_task_without_last_contact_date(
    client, mock_db, mock_task_row, valid_task_payload
):

    valid_task_payload["last_contact_date"] = None

    mock_db.execute.return_value.fetchone.return_value = mock_task_row

    response = client.post("/tasks", json=valid_task_payload)

    assert response.status_code == 201

    sql_params = mock_db.execute.call_args[0][1]

    assert sql_params[5] is None


def test_create_task_invalid_timezone(client, mock_db, valid_task_payload):

    response = client.post(
        "/tasks",
        params={"user_timezone": "Invalid/Timezone"},
        json=valid_task_payload,
    )

    assert response.status_code == 400


def test_create_task_invalid_datetime(client, mock_db, valid_task_payload):

    valid_task_payload["due_date"] = "2026-11-05T12:00:00"

    response = client.post("/tasks", json=valid_task_payload)

    assert response.status_code == 400


def test_create_task_database_error(client, mock_db, valid_task_payload):

    mock_db.execute.side_effect = PsycopgError("Database error")

    response = client.post("/tasks", json=valid_task_payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Database error"


def test_create_task_missing_required_fields(client):

    response = client.post("/tasks", json={"title": "Incomplete task"})

    assert response.status_code == 422


def test_build_task_response(mock_task_row):

    from zoneinfo import ZoneInfo

    result = build_task_response(mock_task_row, ZoneInfo("UTC"))

    assert result.id == 1
    assert result.title == "Follow up with customer"
    assert result.client_id == 10
    assert result.status.value == "Todo"

    assert result.due_date.tzinfo is not None
    assert result.last_contact_date.tzinfo is not None

    assert result.urgency_state is not None
    assert result.urgency_color is not None


def test_build_task_response_null_last_contact(mock_task_row):

    from zoneinfo import ZoneInfo

    row = list(mock_task_row)
    row[6] = None

    result = build_task_response(tuple(row), ZoneInfo("UTC"))

    assert result.last_contact_date is None


def test_get_tasks_filters_by_client_id(client, mock_db, mock_task_row):

    mock_db.execute.return_value.fetchall.return_value = [mock_task_row]

    response = client.get("/tasks", params={"client_id": 10})

    assert response.status_code == 200

    sql_params = mock_db.execute.call_args[0][1]

    assert sql_params == (10,)


@pytest.fixture
def fixed_now():

    return datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def create_task_row(due_date, status="Todo", last_contact_date=None):

    return (
        1,
        "Follow up with customer",
        "Contact customer regarding renewal",
        10,
        status,
        due_date,
        last_contact_date,
    )


def test_get_tasks_calls_sla_calculator(
    client,
    mock_db,
    fixed_now,
    monkeypatch,
):
    sla_spy = MagicMock(side_effect=compute_urgency)

    monkeypatch.setattr(
        "app.api.v1.routers.tasks.compute_urgency",
        sla_spy,
    )

    due_date = fixed_now + timedelta(hours=12)
    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get(
        "/tasks",
        params={
            "client_id": 10,
            "user_timezone": "UTC",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data[0]["urgency_state"] == "DUE_NOW"
    assert data[0]["urgency_color"] == "Red"

    sla_spy.assert_called_once()


def test_get_task_due_now_red(client, mock_db):

    now = datetime.now(UTC)

    due_date = now + timedelta(hours=12)

    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10, "user_timezone": "UTC"})

    assert response.status_code == 200, response.text

    task = response.json()[0]

    assert task["urgency_state"] == UrgencyState.DUE_NOW.value
    assert task["urgency_color"] == "Red"


def test_get_task_upcoming_yellow(client, mock_db):

    now = datetime.now(UTC)

    due_date = now + timedelta(hours=48)

    if now.weekday() >= 4:  # Friday (4), Saturday (5), or Sunday (6)
        due_date = now + timedelta(hours=96)

    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10, "user_timezone": "UTC"})

    assert response.status_code == 200, response.text

    task = response.json()[0]

    assert task["urgency_state"] == UrgencyState.UPCOMING.value
    assert task["urgency_color"] == "Yellow"


def test_get_task_past_due_red(client, mock_db):

    now = datetime.now(UTC)

    due_date = now - timedelta(hours=2)

    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10, "user_timezone": "UTC"})

    assert response.status_code == 200, response.text

    task = response.json()[0]

    assert task["urgency_state"] == "DUE_NOW"
    assert task["urgency_color"] == "Red"


def test_get_resolved_task_green(client, mock_db):

    now = datetime.now(UTC)

    due_date = now - timedelta(days=5)

    row = create_task_row(due_date=due_date, status="Resolved")

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10, "user_timezone": "UTC"})

    assert response.status_code == 200, response.text

    task = response.json()[0]

    assert task["urgency_state"] == "RESOLVED"
    assert task["urgency_color"] == "Green"


def test_task_due_exactly_now_is_red(client, mock_db):

    now = datetime.now(UTC)

    row = create_task_row(now)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10})

    assert response.status_code == 200, response.text

    task = response.json()[0]

    assert task["urgency_state"] == "DUE_NOW"
    assert task["urgency_color"] == "Red"


def test_task_due_in_23_hours_is_red(client, mock_db):

    now = datetime.now(UTC)

    row = create_task_row(now + timedelta(hours=23))

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get("/tasks", params={"client_id": 10})

    task = response.json()[0]

    assert task["urgency_state"] == "DUE_NOW"
    assert task["urgency_color"] == "Red"


def test_get_task_timezone_conversion(client, mock_db):

    due_date = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)

    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchall.return_value = [row]

    response = client.get(
        "/tasks",
        params={"client_id": 10, "user_timezone": "America/New_York"},
    )

    assert response.status_code == 200, response.text

    task = response.json()[0]

    returned_due_date = datetime.fromisoformat(task["due_date"])

    assert returned_due_date.hour == 7

    assert returned_due_date.utcoffset() == timedelta(hours=-5)


def test_get_task_invalid_timezone_returns_400(client):

    response = client.get(
        "/tasks",
        params={"client_id": 10, "user_timezone": "Invalid/Timezone"},
    )

    assert response.status_code == 400


# API + SLA integration tests


def test_create_task_returns_computed_urgency(client, mock_db):

    now = datetime.now(UTC)

    due_date = now + timedelta(hours=10)

    row = create_task_row(due_date)

    mock_db.execute.return_value.fetchone.return_value = row

    payload = {
        "title": "Follow up with customer",
        "description": "Contact customer regarding renewal",
        "client_id": 10,
        "status": "Todo",
        "due_date": due_date.isoformat(),
        "last_contact_date": None,
    }

    response = client.post("/tasks", params={"user_timezone": "UTC"}, json=payload)

    assert response.status_code == 201

    task = response.json()

    assert task["urgency_state"] == "DUE_NOW"
    assert task["urgency_color"] == "Red"


def test_create_future_task_returns_yellow(client, mock_db):

    now = datetime.now(UTC)

    due_date = now + timedelta(days=4)

    row = create_task_row(due_date=due_date)

    mock_db.execute.return_value.fetchone.return_value = row

    payload = {
        "title": "Complet customer follow-up",
        "description": "Waiting for customer response",
        "client_id": 10,
        "status": "Todo",
        "due_date": due_date.isoformat(),
    }

    response = client.post("/tasks", json=payload)

    assert response.status_code == 201

    task = response.json()

    assert task["urgency_state"] == "UPCOMING"
    assert task["urgency_color"] == "Yellow"


def test_create_resolved_task_returns_green(client, mock_db):

    now = datetime.now(UTC)

    due_date = now - timedelta(days=2)

    row = create_task_row(due_date=due_date, status="Resolved")

    mock_db.execute.return_value.fetchone.return_value = row

    payload = {
        "title": "Completed customer follow-up",
        "description": "Customer issue resolved",
        "client_id": 10,
        "status": "Resolved",
        "due_date": due_date.isoformat(),
    }

    response = client.post("/tasks", json=payload)

    assert response.status_code == 201

    task = response.json()

    assert task["urgency_state"] == "RESOLVED"
    assert task["urgency_color"] == "Green"
