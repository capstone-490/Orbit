from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.routers import sessions


def test_login_returns_httponly_session_cookie(monkeypatch):
    monkeypatch.setenv("ORBIT_AUTH_SECRET", "test-secret-with-at-least-32-bytes")
    cursor = MagicMock()
    cursor.fetchone.return_value = (7, auth.hash_password("correct-horse"))
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
    assert auth.get_current_advisor(authorization=None, session_token=token) == {"id": 7}

    session_client = TestClient(app, cookies={"orbit_session": token})
    session_response = session_client.get("/auth/me")
    assert session_response.status_code == 200
    assert session_response.json() == {"id": 7}


def test_login_rejects_invalid_password(monkeypatch):
    cursor = MagicMock()
    cursor.fetchone.return_value = (7, auth.hash_password("correct-horse"))
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


def test_protected_client_endpoint_rejects_missing_token():
    response = TestClient(app).get("/clients")

    assert response.status_code == 401


def test_logout_clears_session_cookie():
    response = TestClient(app).post("/auth/logout")

    assert response.status_code == 200
    assert response.cookies.get("orbit_session") is None