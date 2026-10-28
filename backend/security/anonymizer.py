from __future__ import annotations

import hashlib
import hmac
import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import date

MIN_SECRET_LENGTH = 32


class TokenStore:
    """Keep generated values in memory without retaining the original PII."""

    def __init__(self, secret: bytes | None = None, max_entries: int = 10_000):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._secret = secret if secret is not None else self._load_secret()
        self._max_entries = max_entries
        self._values: OrderedDict[bytes, str] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _load_secret() -> bytes:
        configured = os.getenv("ORBIT_ANONYMIZATION_SECRET")
        if configured is None or not configured.strip():
            raise RuntimeError(
                "ORBIT_ANONYMIZATION_SECRET must be configured and non-empty"
            )
        if len(configured) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"ORBIT_ANONYMIZATION_SECRET must be at least {MIN_SECRET_LENGTH} "
                "characters long"
            )
        return configured.encode("utf-8")

    def get_or_create(
        self,
        field: str,
        value: str,
        factory: Callable[[str], str],
    ) -> str:
        key = hmac.new(
            self._secret,
            f"{field}:{value}".encode(),
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
    """Generate deterministic synthetic values correlated by client identity."""

    def __init__(self, store: TokenStore | None = None):
        self._store = store or TokenStore()

    def anonymize(self, client: dict, client_key: str) -> dict:
        if not client_key or not client_key.strip():
            raise ValueError("client_key must be a non-empty synthetic identifier")

        result = dict(client)
        result["age"] = None
        result["name"] = self._store.get_or_create(
            f"{client_key}:name", client_key, lambda token: f"Client {token[:12]}"
        )
        result["email"] = self._store.get_or_create(
            f"{client_key}:email",
            client_key,
            lambda token: f"client-{token}@example.com",
        )
        result["phone_number"] = self._store.get_or_create(
            f"{client_key}:phone_number",
            client_key,
            _fake_phone,
        )
        result["address"] = self._optional_value(
            client_key,
            "address",
            client.get("address"),
            lambda token: f"Synthetic Address {token[:16]}",
        )
        result["occupation"] = self._optional_value(
            client_key,
            "occupation",
            client.get("occupation"),
            lambda token: f"Synthetic Occupation {token[:12]}",
        )
        if client.get("date_of_birth"):
            birth_date = client["date_of_birth"]
            if isinstance(birth_date, str):
                birth_date = date.fromisoformat(birth_date)
            today = date.today()
            result["age"] = (
                today.year
                - birth_date.year
                - ((today.month, today.day) < (birth_date.month, birth_date.day))
            )
        result.pop("date_of_birth", None)
        result["anonymized_client_id"] = client_key
        return result

    def _optional_value(
        self,
        client_key: str,
        field: str,
        value: str | None,
        factory: Callable[[str], str],
    ) -> str | None:
        if value is None or not value.strip():
            return None
        return self._store.get_or_create(f"{client_key}:{field}", client_key, factory)


def _fake_phone(token: str) -> str:
    number = int(token[:12], 16) % 8_000_000 + 2_000_000
    return f"+1-555-{number // 10_000}-{number % 10_000:04d}"
