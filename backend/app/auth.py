# Substantial AI assistance used; verified with backend tests and live auth smoke test.
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Cookie, Header, HTTPException

PASSWORD_HASH_ITERATIONS = 600_000
TOKEN_LIFETIME_SECONDS = 60 * 60


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_HASH_ITERATIONS,
        _encode(salt),
        _encode(digest),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            _decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_encode(digest), expected_digest)
    except (ValueError, TypeError):
        return False


def create_access_token(advisor_id: int) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(advisor_id),
        "iat": now,
        "exp": now + TOKEN_LIFETIME_SECONDS,
    }
    signing_input = f"{_encode_json(header)}.{_encode_json(payload)}"
    signature = hmac.new(_secret(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_encode(signature)}"


def get_current_advisor(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias="orbit_session"),
) -> dict[str, int]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token
    else:
        raise _unauthorized()

    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = hmac.new(
            _secret(), signing_input.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_decode(signature_part), expected_signature):
            raise ValueError("Invalid signature")

        header = json.loads(_decode(header_part))
        payload = json.loads(_decode(payload_part))
        advisor_id = int(payload["sub"])
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Invalid token header")
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("Expired token")
        if advisor_id <= 0:
            raise ValueError("Invalid advisor")
        return {"id": advisor_id}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, RuntimeError):
        raise _unauthorized() from None


def _secret() -> bytes:
    secret = os.environ.get("ORBIT_AUTH_SECRET", "").encode()
    if len(secret) < 32:
        raise RuntimeError("ORBIT_AUTH_SECRET must contain at least 32 bytes")
    return secret


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode_json(value: dict) -> str:
    return _encode(json.dumps(value, separators=(",", ":")).encode())


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )