"""Tests for the password recovery flow.

These run against an in-memory fake of the database layer, so they need no
Postgres. They exercise the real router, real token hashing and real Argon2
password hashing.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers import password_reset
from app.security.passwords import hash_password, verify_password

OLD_PASSWORD = "OldPassword123!"
NEW_PASSWORD = "BrandNewPass456!"
EMAIL = "advisor@example.com"


class FakeDB:
    """Minimal in-memory stand-in for the two tables the flow touches."""

    def __init__(self):
        self.advisors = [
            {
                "id": 1,
                "username": "advisor",
                "email": EMAIL,
                "password_hash": hash_password(OLD_PASSWORD),
            }
        ]
        self.tokens = []
        self._next_id = 1

    # connection protocol
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return FakeCursor(self)


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def fetchone(self):
        return self._row

    def execute(self, sql, params=()):
        sql = " ".join(sql.split())
        now = datetime.now(UTC)
        self._row = None

        if sql.startswith("SELECT id, username FROM t_advisors WHERE email"):
            for advisor in self.db.advisors:
                if advisor["email"] == params[0]:
                    self._row = (advisor["id"], advisor["username"])

        elif sql.startswith(
            "UPDATE password_reset_tokens SET used_at = now() WHERE advisor_id"
        ):
            for token in self.db.tokens:
                if token["advisor_id"] == params[0] and token["used_at"] is None:
                    token["used_at"] = now

        elif sql.startswith("INSERT INTO password_reset_tokens"):
            advisor_id, token_hash, expires_at = params
            self.db.tokens.append(
                {
                    "id": self.db._next_id,
                    "advisor_id": advisor_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at,
                    "used_at": None,
                }
            )
            self.db._next_id += 1

        elif sql.startswith("SELECT 1 FROM password_reset_tokens"):
            for token in self.db.tokens:
                if (
                    token["token_hash"] == params[0]
                    and token["used_at"] is None
                    and token["expires_at"] > now
                ):
                    self._row = (1,)

        elif sql.startswith(
            "UPDATE password_reset_tokens SET used_at = now() WHERE token_hash"
        ):
            for token in self.db.tokens:
                if (
                    token["token_hash"] == params[0]
                    and token["used_at"] is None
                    and token["expires_at"] > now
                ):
                    token["used_at"] = now
                    self._row = (token["advisor_id"],)
                    break

        elif sql.startswith("UPDATE t_advisors SET password_hash"):
            password_hash, advisor_id = params
            for advisor in self.db.advisors:
                if advisor["id"] == advisor_id:
                    advisor["password_hash"] = password_hash

        else:  # pragma: no cover - guards against silently ignoring new queries
            raise AssertionError(f"Unexpected SQL in test: {sql}")


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(password_reset, "get_connection", lambda: fake)
    return fake


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []
    monkeypatch.setattr(
        password_reset,
        "send_email",
        lambda to, subject, body: sent.append(
            {"to": to, "subject": subject, "body": body}
        ),
    )
    return sent


@pytest.fixture
def client(db, sent_emails):
    app = FastAPI()
    app.include_router(password_reset.router, prefix="/api/v1")
    return TestClient(app)


def request_reset(client, sent_emails, email=EMAIL):
    response = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    return sent_emails[-1]["body"] if sent_emails else None


def extract_token(body):
    match = re.search(r"token=([\w\-]+)", body)
    assert match, "reset link with token not found in email body"
    return match.group(1)


# ---------- forgot-password ----------


def test_forgot_password_sends_reset_link_to_registered_email(client, sent_emails):
    response = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})

    assert response.status_code == 200
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == EMAIL
    assert "/reset-password?token=" in sent_emails[0]["body"]


def test_forgot_password_is_case_insensitive(client, sent_emails):
    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "Advisor@Example.COM"}
    )

    assert response.status_code == 200
    assert len(sent_emails) == 1


def test_forgot_password_gives_same_response_for_unknown_email(client, sent_emails, db):
    known = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    unknown = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )

    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()
    # Only the known account produced an email and a token.
    assert len(sent_emails) == 1
    assert len(db.tokens) == 1


@pytest.mark.parametrize(
    "bad_email", ["", "not-an-email", "missing@tld", "@example.com"]
)
def test_forgot_password_rejects_invalid_email(client, sent_emails, bad_email):
    response = client.post("/api/v1/auth/forgot-password", json={"email": bad_email})

    assert response.status_code == 422
    assert sent_emails == []


def test_only_token_hash_is_stored(client, sent_emails, db):
    body = request_reset(client, sent_emails)
    token = extract_token(body)

    assert len(db.tokens) == 1
    assert token != db.tokens[0]["token_hash"]
    assert token not in db.tokens[0]["token_hash"]


def test_new_request_invalidates_previous_link(client, sent_emails):
    first = extract_token(request_reset(client, sent_emails))
    second = extract_token(request_reset(client, sent_emails))

    assert first != second
    assert (
        client.get(
            "/api/v1/auth/reset-password/validate", params={"token": first}
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/auth/reset-password/validate", params={"token": second}
        ).status_code
        == 200
    )


# ---------- validate ----------


def test_validate_accepts_fresh_token(client, sent_emails):
    token = extract_token(request_reset(client, sent_emails))

    response = client.get(
        "/api/v1/auth/reset-password/validate", params={"token": token}
    )

    assert response.status_code == 200


def test_validate_rejects_unknown_token(client):
    response = client.get(
        "/api/v1/auth/reset-password/validate", params={"token": "x" * 43}
    )

    assert response.status_code == 400
    assert "invalid or has expired" in response.json()["detail"]


def test_validate_rejects_expired_token(client, sent_emails, db):
    token = extract_token(request_reset(client, sent_emails))
    db.tokens[0]["expires_at"] = datetime.now(UTC) - timedelta(minutes=1)

    response = client.get(
        "/api/v1/auth/reset-password/validate", params={"token": token}
    )

    assert response.status_code == 400


# ---------- reset-password ----------


def test_reset_password_updates_password_so_new_one_works(client, sent_emails, db):
    token = extract_token(request_reset(client, sent_emails))

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD}
    )

    assert response.status_code == 200
    stored_hash = db.advisors[0]["password_hash"]
    assert verify_password(NEW_PASSWORD, stored_hash)
    assert not verify_password(OLD_PASSWORD, stored_hash)


def test_reset_token_cannot_be_used_twice(client, sent_emails, db):
    token = extract_token(request_reset(client, sent_emails))

    first = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD}
    )
    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "AnotherPass789!!"},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    # The second attempt must not have changed the password.
    assert verify_password(NEW_PASSWORD, db.advisors[0]["password_hash"])


def test_reset_rejects_expired_token(client, sent_emails, db):
    token = extract_token(request_reset(client, sent_emails))
    db.tokens[0]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD}
    )

    assert response.status_code == 400
    assert verify_password(OLD_PASSWORD, db.advisors[0]["password_hash"])


def test_reset_rejects_unknown_token(client, db):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "z" * 43, "password": NEW_PASSWORD},
    )

    assert response.status_code == 400
    assert verify_password(OLD_PASSWORD, db.advisors[0]["password_hash"])


@pytest.mark.parametrize("bad_password", ["short", "a" * 11, "a" * 129])
def test_reset_enforces_password_requirements(client, sent_emails, db, bad_password):
    token = extract_token(request_reset(client, sent_emails))

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": bad_password}
    )

    assert response.status_code == 422
    # A rejected password must not burn the token; the advisor can retry.
    assert db.tokens[0]["used_at"] is None
    assert verify_password(OLD_PASSWORD, db.advisors[0]["password_hash"])
