from __future__ import annotations

import hashlib
import hmac
import re
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import ClassVar
from uuid import uuid4

from app.core.config import get_settings
from app.core.security.patterns import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    SIN_PATTERN,
)
from app.core.security.redactor import REDACTED

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


class MaskingContext:
    """Request-local reversible masking for AI prompts.

    Original values are retained only for the lifetime of this
    context and must never be sent to an external provider.
    """

    FIELDS: ClassVar[dict[str, str]] = {
        "name": "NAME",
        "email": "EMAIL",
        "phone_number": "PHONE",
        "address": "ADDRESS",
        "occupation": "OCCUPATION",
    }

    def __init__(self, clients: list[dict]) -> None:
        self._namespace = uuid4().hex[:16]
        self._originals: dict[str, str] = {}
        self._tokens: dict[tuple[str, str], str] = {}

        known_values = {}

        for client in clients:
            for field, kind in self.FIELDS.items():
                value = client.get(field)

                if isinstance(value, str) and value.strip():
                    known_values[value.strip()] = kind

        self._known_patterns = [
            (
                re.compile(
                    r"(?<!\w)" + re.escape(value) + r"(?!\w)",
                    re.IGNORECASE,
                ),
                kind,
            )
            for value, kind in known_values.items()
        ]

    def _placeholder(self, kind: str, value: str) -> str:
        key = (kind, value)

        if key not in self._tokens:
            token = f"[{kind}_{self._namespace}_{len(self._tokens) + 1}]"
            self._tokens[key] = token
            self._originals[token] = value

        return self._tokens[key]

    def _mask_text(self, text: str) -> str:
        matches = []

        patterns = [
            (EMAIL_PATTERN, "EMAIL"),
            (PHONE_PATTERN, "PHONE"),
            (SIN_PATTERN, "SIN"),
            *self._known_patterns,
        ]

        for pattern, kind in patterns:
            for match in pattern.finditer(text):
                matches.append((match.start(), match.end(), kind))

        if not matches:
            return text

        matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))

        merged = []

        for start, end, kind in matches:
            if merged and start < merged[-1][1]:
                previous_start, previous_end, previous_kind = merged[-1]

                merged[-1] = (
                    previous_start,
                    max(previous_end, end),
                    "SIN" if "SIN" in (previous_kind, kind) else previous_kind,
                )
            else:
                merged.append((start, end, kind))

        parts = []
        cursor = 0

        for start, end, kind in merged:
            parts.append(text[cursor:start])

            if kind == "SIN":
                parts.append(REDACTED)
            else:
                parts.append(self._placeholder(kind, text[start:end]))

            cursor = end

        parts.append(text[cursor:])

        return "".join(parts)

    def mask(self, value):
        """Return a masked copy without modifying the input."""
        if isinstance(value, str):
            return self._mask_text(value)

        if isinstance(value, dict):
            return {key: self.mask(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self.mask(item) for item in value]

        if isinstance(value, tuple):
            return tuple(self.mask(item) for item in value)

        return value

    def has_unknown_placeholders(self, text: str) -> bool:
        """Detect placeholders not generated by this context."""
        pattern = re.compile(
            r"\[(?:NAME|EMAIL|PHONE|ADDRESS|OCCUPATION)_[^\]\r\n]*\]",
            re.IGNORECASE,
        )

        return any(
            match.group(0) not in self._originals for match in pattern.finditer(text)
        )

    def restore(self, text: str) -> str:
        """Restore only placeholders generated by this context."""
        if not self._originals:
            return text

        pattern = re.compile("|".join(re.escape(token) for token in self._originals))

        return pattern.sub(
            lambda match: self._originals[match.group(0)],
            text,
        )
