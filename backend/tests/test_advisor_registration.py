
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.main import app
from app.security.passwords import hash_password, verify_password

client = TestClient(app)

VALID_ADVISOR = {
    "username": "Test Advisor",
    "email": "advisor@example.com",
    "password": "SecurePassword123!",
}


def test_password_hashing():
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword123!", hashed)


@patch("app.routers.advisor.get_connection")
def test_successful_registration(mock_get_connection):
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        1,
        "Test Advisor",
        "advisor@example.com",
    )

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    mock_get_connection.return_value = connection

    response = client.post("/auth/register", json=VALID_ADVISOR)

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "username": "Test Advisor",
        "email": "advisor@example.com",
    }

    inserted_values = cursor.execute.call_args.args[1]
    assert inserted_values[0] == "Test Advisor"
    assert inserted_values[1] == "advisor@example.com"
    assert inserted_values[2] != VALID_ADVISOR["password"]
    assert verify_password(
        VALID_ADVISOR["password"], inserted_values[2]
    )


def test_invalid_email():
    response = client.post(
        "/auth/register",
        json={**VALID_ADVISOR, "email": "not-an-email"},
    )

    assert response.status_code == 422


def test_short_password():
    response = client.post(
        "/auth/register",
        json={**VALID_ADVISOR, "password": "short"},
    )

    assert response.status_code == 422


def test_missing_required_field():
    data = VALID_ADVISOR.copy()
    del data["username"]

    response = client.post("/auth/register", json=data)

    assert response.status_code == 422


def test_blank_username():
    response = client.post(
        "/auth/register",
        json={**VALID_ADVISOR, "username": "   "},
    )

    assert response.status_code == 422


@patch("app.routers.advisor.get_connection")
def test_duplicate_email(mock_get_connection):
    cursor = MagicMock()
    cursor.execute.side_effect = UniqueViolation(
        "duplicate key value violates unique constraint"
    )

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    mock_get_connection.return_value = connection

    response = client.post("/auth/register", json=VALID_ADVISOR)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An account with this email already exists."
    )
