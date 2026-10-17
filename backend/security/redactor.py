from __future__ import annotations

import traceback
from typing import Any

from .patterns import PII_PATTERN

REDACTED = "[REDACTED]"


def redact_text(text_to_redact: str) -> str:
    if not isinstance(text_to_redact, str):
        raise TypeError("redact_text expects a string")
    return PII_PATTERN.sub(REDACTED, text_to_redact)


def redact_data(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            redact_text(key) if isinstance(key, str) else key: redact_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    return value


def redact_exception(exc: BaseException) -> str:
    if not isinstance(exc, BaseException):
        raise TypeError("redact_exception expects an exception")
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return redact_text(formatted)
