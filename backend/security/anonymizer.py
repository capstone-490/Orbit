from __future__ import annotations

import hashlib
import hmac
import os
import threading
from collections import OrderedDict
from collections.abc import Callable

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


def mask_for_ai(client: dict, store: TokenStore | None = None) -> dict:
    """Return a deterministic, non-PII representation for an AI request."""
    client_id = client.get("id")
    if client_id is None:
        raise ValueError("client must include a stable id")

    token_store = store or TokenStore()
    result = dict(client)
    result["name"] = token_store.get_or_create(
        "name",
        str(client_id),
        lambda token: f"Client {token[:12]}",
    )
    result["email"] = token_store.get_or_create(
        "email",
        str(client_id),
        lambda token: f"client-{token}@example.com",
    )
    result["phone_number"] = token_store.get_or_create(
        "phone_number",
        str(client_id),
        _fake_phone,
    )
    result["address"] = _optional_mask(
        token_store,
        "address",
        client.get("address"),
        str(client_id),
        lambda token: f"Synthetic Address {token[:16]}",
    )
    result["occupation"] = _optional_mask(
        token_store,
        "occupation",
        client.get("occupation"),
        str(client_id),
        lambda token: f"Synthetic Occupation {token[:12]}",
    )
    return result


def _optional_mask(
    store: TokenStore,
    field: str,
    value: str | None,
    client_id: str,
    factory: Callable[[str], str],
) -> str | None:
    if value is None or not value.strip():
        return None
    return store.get_or_create(field, client_id, factory)


def _fake_phone(token: str) -> str:
    number = int(token[:12], 16) % 8_000_000 + 2_000_000
    return f"+1-555-{number // 10_000}-{number % 10_000:04d}"
