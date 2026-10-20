from datetime import UTC
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

import main
from main import ClientCreate

client = TestClient(main.app)

COLUMNS = [
    "id",
    "name",
    "email",
    "phone_number",
    "address",
    "date_of_birth",
    "occupation",
    "risk_tolerance",
    "target_retirement_age",
    "timeline",
    "created_at",
]


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setattr(main, "get_connection", lambda: conn)

    return cursor


def test_create_client_success(mock_db):
    mock_db.fetchone.return_value = (1,)

    response = client.post(
        "/clients",
        json={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone_number": "514-555-1234",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "message": "Client created successfully",
    }

    mock_db.execute.assert_called_once()
    query, params = mock_db.execute.call_args.args

    assert "INSERT INTO clients" in query
    assert params["name"] == "Alice Smith"
    assert params["email"] == "alice@example.com"
    assert params["phone_number"] == "514-555-1234"


@pytest.mark.parametrize("missing_field", ["name", "email", "phone_number"])
def test_create_client_missing_required_field(mock_db, missing_field):
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
    }
    del payload[missing_field]

    response = client.post("/clients", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("email", "not-an-email"),
        ("phone_number", ""),
        ("target_retirement_age", -1),
        ("target_retirement_age", 121),
        ("risk_tolerance", "Unknown"),
    ],
)
def test_create_client_invalid_fields(mock_db, field, value):
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
    }
    payload[field] = value

    response = client.post("/clients", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


@pytest.mark.parametrize(
    "phone",
    ["12345", "abcdefghij", "111-111-1111", "514-ABC-1234"],
)
def test_invalid_phone_number(phone):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClientCreate(
            name="Test Client",
            email="test@example.com",
            phone_number=phone,
        )


def test_create_client_optional_fields(mock_db):
    mock_db.fetchone.return_value = (2,)

    response = client.post(
        "/clients",
        json={
            "name": "Bob Jones",
            "email": "bob@example.com",
            "phone_number": "514-555-5678",
        },
    )

    assert response.status_code == 201

    _, params = mock_db.execute.call_args.args

    assert params["address"] is None
    assert params["date_of_birth"] is None
    assert params["occupation"] is None
    assert params["risk_tolerance"] is None
    assert params["target_retirement_age"] is None
    assert params["timeline"] is None


def test_create_client_duplicate(mock_db):
    mock_db.execute.side_effect = UniqueViolation("Duplicate client")

    response = client.post(
        "/clients",
        json={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone_number": "514-555-1234",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_clients(mock_db):
    from datetime import datetime

    mock_db.description = [MagicMock(name="column") for _ in COLUMNS]

    for column, name in zip(mock_db.description, COLUMNS):
        column.name = name

    mock_db.fetchall.return_value = [
        (
            1,
            "Alice Smith",
            "alice@example.com",
            "514-555-1234",
            None,
            None,
            None,
            None,
            None,
            None,
            datetime(2026, 10, 15, tzinfo=UTC),
        )
    ]

    response = client.get("/clients")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Alice Smith"
    assert response.json()[0]["email"] == "alice@example.com"


def test_list_clients_empty(mock_db):
    mock_db.description = [MagicMock(name="column") for _ in COLUMNS]

    for column, name in zip(mock_db.description, COLUMNS):
        column.name = name

    mock_db.fetchall.return_value = []

    response = client.get("/clients")

    assert response.status_code == 200
    assert response.json() == []
