from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import date, timedelta


class TokenStore:
    """Keep generated values in memory without retaining the original PII."""

    def __init__(self, secret: bytes | None = None, max_entries: int = 10_000):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._secret = secret or self._load_secret()
        self._max_entries = max_entries
        self._values: OrderedDict[bytes, str] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _load_secret() -> bytes:
        configured = os.getenv("ORBIT_ANONYMIZATION_SECRET")
        if configured:
            return configured.encode("utf-8")
        return secrets.token_bytes(32)

    def get_or_create(
        self,
        field: str,
        value: str,
        factory: Callable[[str], str],
    ) -> str:
        normalized = value.strip().casefold()
        key = hmac.new(
            self._secret,
            f"{field}:{normalized}".encode(),
            hashlib.sha256,
        ).digest()
        token = key.hex()[:24]
        with self._lock:
            existing = self._values.get(key)
            if existing is not None:
                self._values.move_to_end(key)
                return existing
            generated = factory(token)
            self._values[key] = generated
            self._values.move_to_end(key)
            if len(self._values) > self._max_entries:
                self._values.popitem(last=False)
            return generated


class ClientAnonymizer:
    """Generate deterministic, clearly synthetic values for client records."""

    def __init__(self, store: TokenStore | None = None):
        self._store = store or TokenStore()

    def _value(self, field: str, value: str | None, factory: Callable[[str], str]):
        if value is None or not value.strip():
            return None
        return self._store.get_or_create(field, value, factory)

    def anonymize(self, client: dict) -> dict:
        result = dict(client)
        result["name"] = self._value("name", client["name"], lambda token: f"Client {token[:12]}")
        result["email"] = self._value(
            "email", client["email"], lambda token: f"client-{token}@example.com"
        )
        result["phone_number"] = self._value(
            "phone_number",
            client["phone_number"],
            lambda token: _fake_phone(token),
        )
        result["address"] = self._value(
            "address", client.get("address"), lambda token: f"Synthetic Address {token[:16]}"
        )
        result["occupation"] = self._value(
            "occupation", client.get("occupation"), lambda token: f"Synthetic Occupation {token[:12]}"
        )
        if client.get("date_of_birth"):
            result["date_of_birth"] = self._store.get_or_create(
                "date_of_birth",
                str(client["date_of_birth"]),
                lambda token: date(1960, 1, 1)
                + timedelta(days=int(token[:6], 16) % (40 * 365)),
            )
        return result


def _fake_phone(token: str) -> str:
    number = int(token[:12], 16) % 8_000_000 + 2_000_000
    return f"+1-555-{number // 10_000}-{number % 10_000:04d}"


client_anonymizer = ClientAnonymizer()