# AI assistance used; tests require local validation.
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routers import notes
from app.auth import create_access_token
from app.main import app

NOTES_URL = "/api/v1/clients/1/notes"

COLUMNS = [
    "id",
    "title",
    "content",
    "client_id",
    "author_id",
    "author_type",
    "created_at",
    "updated_at",
]

NOTE_DATE = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)

NOTE_PAYLOAD = {
    "title": "Investment discussion",
    "content": "Discussed investment goals.",
}

NOTE_ROW = (
    1,
    "Investment discussion",
    "Discussed investment goals.",
    1,
    1,
    "Advisor",
    NOTE_DATE,
    NOTE_DATE,
)


@pytest.fixture
def notes_client():
    return TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(1)}"},
    )


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor

    cursor.description = [SimpleNamespace(name=name) for name in COLUMNS]

    monkeypatch.setattr(
        notes,
        "get_connection",
        lambda user_id=None, user_type="System": conn,
    )

    return cursor


# POST: Create a note successfully
def test_create_note_success(notes_client, mock_db):
    mock_db.fetchone.side_effect = [(1,), NOTE_ROW]

    response = notes_client.post(
        NOTES_URL,
        json=NOTE_PAYLOAD,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == NOTE_PAYLOAD["title"]
    assert data["content"] == NOTE_PAYLOAD["content"]
    assert data["client_id"] == 1
    assert data["author_id"] == 1
    assert data["author_type"] == "Advisor"

    assert datetime.fromisoformat(data["created_at"]) == NOTE_DATE
    assert datetime.fromisoformat(data["updated_at"]) == NOTE_DATE

    assert mock_db.execute.call_count == 2

    query, params = mock_db.execute.call_args.args

    assert "INSERT INTO t_notes" in query
    assert params["client_id"] == 1
    assert params["author_id"] == 1
    assert params["title"] == NOTE_PAYLOAD["title"]
    assert params["content"] == NOTE_PAYLOAD["content"]


# GET: Retrieve existing notes
def test_list_notes_success(notes_client, mock_db):
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [NOTE_ROW]

    response = notes_client.get(NOTES_URL)

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["title"] == NOTE_PAYLOAD["title"]
    assert data[0]["content"] == NOTE_PAYLOAD["content"]
    assert data[0]["client_id"] == 1


# GET: Client without notes
def test_list_notes_empty(notes_client, mock_db):
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = []

    response = notes_client.get(NOTES_URL)

    assert response.status_code == 200
    assert response.json() == []


# GET: Notes ordered newest first
def test_list_notes_newest_first(notes_client, mock_db):
    newer_date = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)

    newer_note = (
        2,
        "Newer note",
        "Recent meeting preparation.",
        1,
        1,
        "Advisor",
        newer_date,
        newer_date,
    )

    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [
        newer_note,
        NOTE_ROW,
    ]

    response = notes_client.get(NOTES_URL)

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["id"] == 2
    assert data[1]["id"] == 1

    query, params = mock_db.execute.call_args.args

    assert "ORDER BY created_at DESC, id DESC" in query
    assert params["client_id"] == 1


# POST: Reject invalid note fields
@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ""),
        ("title", "   "),
        ("title", "x" * 201),
        ("content", ""),
        ("content", "   "),
        ("content", "x" * 5001),
        ("title", None),
        ("content", None),
    ],
)
def test_create_note_invalid_fields(
    notes_client,
    mock_db,
    field,
    value,
):
    payload = NOTE_PAYLOAD.copy()
    payload[field] = value

    response = notes_client.post(
        NOTES_URL,
        json=payload,
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


# POST: Reject missing required fields
@pytest.mark.parametrize(
    "missing_field",
    ["title", "content"],
)
def test_create_note_missing_field(
    notes_client,
    mock_db,
    missing_field,
):
    payload = NOTE_PAYLOAD.copy()
    del payload[missing_field]

    response = notes_client.post(
        NOTES_URL,
        json=payload,
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


# POST: Remove surrounding whitespace
def test_create_note_trims_whitespace(
    notes_client,
    mock_db,
):
    mock_db.fetchone.side_effect = [(1,), NOTE_ROW]

    response = notes_client.post(
        NOTES_URL,
        json={
            "title": "  Investment discussion  ",
            "content": "  Discussed investment goals.  ",
        },
    )

    assert response.status_code == 201

    _, params = mock_db.execute.call_args.args

    assert params["title"] == NOTE_PAYLOAD["title"]
    assert params["content"] == NOTE_PAYLOAD["content"]


# GET and POST: Client does not exist
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_client_not_found(
    notes_client,
    mock_db,
    method,
):
    mock_db.fetchone.return_value = None

    kwargs = {"json": NOTE_PAYLOAD} if method == "POST" else {}

    response = notes_client.request(
        method,
        "/api/v1/clients/999/notes",
        **kwargs,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."

    mock_db.execute.assert_called_once()


# GET and POST: Another advisor cannot access notes
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_notes_other_advisor_forbidden(mock_db, method):
    other_advisor = TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(2)}"},
    )

    mock_db.fetchone.return_value = None

    kwargs = {"json": NOTE_PAYLOAD} if method == "POST" else {}

    response = other_advisor.request(
        method,
        NOTES_URL,
        **kwargs,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found."

    mock_db.execute.assert_called_once()

    query, params = mock_db.execute.call_args.args

    assert "AND advisor_id = %(advisor_id)s" in query
    assert params["advisor_id"] == 2
    assert params["client_id"] == 1


# GET and POST: Authentication required
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_notes_unauthenticated(mock_db, method):
    unauthenticated_client = TestClient(app)

    kwargs = {"json": NOTE_PAYLOAD} if method == "POST" else {}

    response = unauthenticated_client.request(
        method,
        NOTES_URL,
        **kwargs,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."

    mock_db.execute.assert_not_called()


# GET and POST: Invalid client ID
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_notes_invalid_client_id(
    notes_client,
    mock_db,
    method,
):
    kwargs = {"json": NOTE_PAYLOAD} if method == "POST" else {}

    response = notes_client.request(
        method,
        "/api/v1/clients/invalid/notes",
        **kwargs,
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


# POST: Author identity cannot be supplied by the caller
def test_create_note_uses_authenticated_author(
    notes_client,
    mock_db,
):
    mock_db.fetchone.side_effect = [(1,), NOTE_ROW]

    response = notes_client.post(
        NOTES_URL,
        json={
            **NOTE_PAYLOAD,
            "author_id": 999,
            "author_type": "Agent",
            "client_id": 999,
        },
    )

    assert response.status_code == 201
    assert response.json()["author_id"] == 1
    assert response.json()["author_type"] == "Advisor"
    assert response.json()["client_id"] == 1

    query, params = mock_db.execute.call_args.args

    assert params["author_id"] == 1
    assert params["client_id"] == 1
    assert "'Advisor'" in query
