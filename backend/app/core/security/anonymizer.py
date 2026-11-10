from __future__ import annotations

import hashlib
import hmac
import threading
from collections import OrderedDict
from collections.abc import Callable

from app.core.config import get_settings

MIN_SECRET_LENGTH = 32


class TokenStore:
    """Keep generated values in memory without retaining the original PII."""

    def __init__(
        self,
        secret: str | bytes | None = None,
        max_entries: int = 10_000,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")

        if secret is None:
            secret_bytes = self._load_secret()
        else:
            secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret

            if not secret_bytes or not secret_bytes.strip():
                raise RuntimeError(
                    "ORBIT_ANONYMIZATION_SECRET must be secret and non-empty"
                )

            if len(secret_bytes) < MIN_SECRET_LENGTH:
                raise RuntimeError(
                    f"ORBIT_ANONYMIZATION_SECRET must be at least "
                    f"{MIN_SECRET_LENGTH} bytes long"
                )

        self._secret: bytes = secret_bytes
        self._max_entries = max_entries
        self._values: OrderedDict[bytes, str] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _load_secret() -> bytes:
        secret = get_settings().ORBIT_ANONYMIZATION_SECRET

        if secret is None or not secret.strip():
            raise RuntimeError(
                "ORBIT_ANONYMIZATION_SECRET must be secret and non-empty"
            )
        if len(secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"ORBIT_ANONYMIZATION_SECRET must be at least "
                f"{MIN_SECRET_LENGTH} bytes long"
            )
        return secret.encode("utf-8")

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


def mask_for_ai(
    client: dict,
    store: TokenStore,
) -> dict:
    """Return a deterministic, non-PII representation for an AI request."""

    client_id = client.get("id")

    if client_id is None:
        raise ValueError("client must include a stable id")

    result = dict(client)

    result["name"] = store.get_or_create(
        "name",
        str(client_id),
        lambda token: f"Client {token[:12]}",
    )

    result["email"] = store.get_or_create(
        "email",
        str(client_id),
        lambda token: f"client-{token}@example.com",
    )

    result["phone_number"] = store.get_or_create(
        "phone_number",
        str(client_id),
        _fake_phone,
    )

    result["address"] = _optional_mask(
        store,
        "address",
        client.get("address"),
        str(client_id),
        lambda token: f"Synthetic Address {token[:16]}",
    )

    result["occupation"] = _optional_mask(
        store,
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
