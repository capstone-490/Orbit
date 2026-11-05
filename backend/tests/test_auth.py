# Substantial AI assistance used; verified with backend tests and live auth smoke test.
import hashlib
import hmac
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth
from app.api.routers import sessions
from app.main import app
from app.security.passwords import hash_password


def _signed_token(payload, secret, header=None):
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{auth._encode_json(header)}.{auth._encode_json(payload)}"
    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{auth._encode(signature)}"


def test_legacy_password_hash_round_trip():
    password = "legacy-password"
    stored_hash = auth.hash_password(password)

    assert auth.verify_password(password, stored_hash)
    assert not auth.verify_password("incorrect-password", stored_hash)


def test_login_returns_httponly_session_cookie(monkeypatch):
    monkeypatch.setenv("ORBIT_AUTH_SECRET", "test-secret-with-at-least-32-bytes")
    cursor = MagicMock()
    cursor.fetchone.return_value = (7, hash_password("correct-horse"))
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(sessions, "get_connection", lambda: connection)

    response = TestClient(app).post(
        "/auth/login",
        json={"email": "advisor@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["advisor"] == {"id": 7, "email": "advisor@example.com"}
    token = response.cookies["orbit_session"]
    assert auth.get_current_advisor(authorization=None, session_token=token) == {
        "id": 7
    }

    session_client = TestClient(app, cookies={"orbit_session": token})
    session_response = session_client.get("/auth/me")
    assert session_response.status_code == 200
    assert session_response.json() == {"id": 7}


def test_login_rejects_invalid_password(monkeypatch):
    cursor = MagicMock()
    cursor.fetchone.return_value = (7, hash_password("correct-horse"))
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(sessions, "get_connection", lambda: connection)

    response = TestClient(app).post(
        "/auth/login",
        json={"email": "advisor@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_returns_unavailable_when_authentication_is_not_configured(monkeypatch):
    monkeypatch.setenv("ORBIT_AUTH_SECRET", "")
    cursor = MagicMock()
    cursor.fetchone.return_value = (7, hash_password("correct-horse"))
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(sessions, "get_connection", lambda: connection)

    response = TestClient(app).post(
        "/auth/login",
        json={"email": "advisor@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication is not configured."


def test_login_rejects_unknown_email(monkeypatch):
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(sessions, "get_connection", lambda: connection)

    response = TestClient(app).post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_registration_can_be_followed_by_login(monkeypatch):
    cursor = MagicMock()
    stored_advisor = {}

    def execute(query, parameters):
        if query.lstrip().startswith("INSERT INTO advisors"):
            stored_advisor.update(
                username=parameters[0],
                email=parameters[1],
                password_hash=parameters[2],
            )

    def fetchone():
        if stored_advisor:
            if stored_advisor.get("id") is None:
                stored_advisor["id"] = 7
                return (
                    stored_advisor["id"],
                    stored_advisor["username"],
                    stored_advisor["email"],
                )
            return (stored_advisor["id"], stored_advisor["password_hash"])
        return None

    cursor.execute.side_effect = execute
    cursor.fetchone.side_effect = fetchone
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(
        "app.api.routers.advisor_registration.get_connection", lambda: connection
    )
    monkeypatch.setattr(sessions, "get_connection", lambda: connection)

    client = TestClient(app)
    registration = client.post(
        "/auth/register",
        json={
            "username": "Test Advisor",
            "email": "advisor@example.com",
            "password": "SecurePassword123!",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "advisor@example.com", "password": "SecurePassword123!"},
    )

    assert registration.status_code == 201
    assert login.status_code == 200
    assert login.json()["advisor"] == {"id": 7, "email": "advisor@example.com"}
    assert "orbit_session" in login.cookies


def test_protected_client_endpoint_rejects_missing_token():
    response = TestClient(app).get("/clients")

    assert response.status_code == 401


def test_logout_clears_session_cookie():
    response = TestClient(app).post("/auth/logout")

    assert response.status_code == 200
    assert response.cookies.get("orbit_session") is None


@pytest.mark.parametrize("stored_hash", ["pbkdf2_sha256$invalid", "malformed"])
def test_verify_password_rejects_malformed_hash(stored_hash):
    assert not auth.verify_password("password", stored_hash)


def test_verify_password_rejects_type_errors(monkeypatch):
    monkeypatch.setattr(
        auth.hashlib,
        "pbkdf2_hmac",
        MagicMock(side_effect=TypeError("invalid hash input")),
    )

    assert not auth.verify_password("password", "pbkdf2_sha256$1$c2FsdA$ZGlnZXN0")


def test_get_current_advisor_rejects_invalid_signature(monkeypatch):
    secret = "test-secret-with-at-least-32-bytes"
    monkeypatch.setenv("ORBIT_AUTH_SECRET", secret)
    valid_token = auth.create_access_token(7)
    header, payload, _ = valid_token.split(".")
    token = f"{header}.{payload}.{auth._encode(b'invalid-signature')}"

    with pytest.raises(HTTPException) as error:
        auth.get_current_advisor(authorization=f"Bearer {token}")

    assert error.value.status_code == 401


@pytest.mark.parametrize(
    ("header", "payload"),
    [
        ({"alg": "HS384", "typ": "JWT"}, {"sub": "7", "exp": int(time.time()) + 60}),
        ({"alg": "HS256", "typ": "JWT"}, {"sub": "7", "exp": 0}),
        ({"alg": "HS256", "typ": "JWT"}, {"sub": "0", "exp": int(time.time()) + 60}),
        ({"alg": "HS256", "typ": "JWT"}, {"exp": int(time.time()) + 60}),
    ],
)
def test_get_current_advisor_rejects_invalid_claims(monkeypatch, header, payload):
    secret = "test-secret-with-at-least-32-bytes"
    monkeypatch.setenv("ORBIT_AUTH_SECRET", secret)
    token = _signed_token(payload, secret, header)

    with pytest.raises(HTTPException) as error:
        auth.get_current_advisor(authorization=f"Bearer {token}")

    assert error.value.status_code == 401
