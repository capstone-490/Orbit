# 50% or more AI-generated
from __future__ import annotations
import json
import logging
import os
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from security.redactor import REDACTED, redact_data, redact_text

SERVICE_NAME = "orbit-backend"

# Set by the request middleware; read by the formatter so every log line written
# while handling a request carries its id automatically.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has. Anything else on a record came from `extra=`.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",  # Uvicorn's ANSI-coloured duplicate of the message
}

# Python says WARNING; the story asks for INFO / WARN / ERROR.
_LEVEL_NAMES = {"WARNING": "WARN"}
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _safe_default(obj: Any) -> str:
    """json.dumps fallback for objects redact_data doesn't walk (UUID, datetime, models...).

    str() can expose PII, so the string goes through the redactor too.
    """
    if isinstance(obj, BaseException):
        return redact_text(f"{type(obj).__name__}: {obj}")
    return redact_text(str(obj))


# ---- Short, readable stack traces ------------------------------------------
_MIDDLEWARE_FILE = os.path.join("app", "middleware", "request_logging.py")


def _is_noise_frame(filename: str) -> bool:
    return (
        "site-packages" in filename  # installed libraries (FastAPI, Starlette...)
        or filename.startswith("<")  # Python internals like <frozen importlib>
        or f"{os.sep}lib{os.sep}python" in filename  # Python's standard library
        or filename.endswith(_MIDDLEWARE_FILE)  # our middleware: same on every error
    )


def _trim_frames(te: traceback.TracebackException, seen: set[int] | None = None) -> int:
    """Remove library frames in place (also for chained exceptions). Returns how many."""
    seen = seen if seen is not None else set()
    if id(te) in seen:
        return 0
    seen.add(id(te))

    kept = [frame for frame in te.stack if not _is_noise_frame(frame.filename)]
    if not kept and te.stack:  # error raised inside a library: keep the last frame
        kept = [te.stack[-1]]
    hidden = len(te.stack) - len(kept)
    te.stack = traceback.StackSummary.from_list(kept)

    for chained in (te.__cause__, te.__context__):
        if chained is not None:
            hidden += _trim_frames(chained, seen)
    return hidden


def _short_path(filename: str) -> str:
    try:
        return os.path.relpath(filename)
    except ValueError:
        return os.path.basename(filename)


def _format_error(exc: BaseException, full_stack: bool = False) -> dict[str, Any]:
    """Error block for a log line: type, message, where it happened, stack.

    The stack is short (our code only) unless full_stack is True. Either way it
    is redacted with the PII redactor, and again with the rest of the entry.
    """
    te = traceback.TracebackException.from_exception(exc)

    # "location" always points at our own code, even when the full stack is kept.
    own_frames = [f for f in te.stack if not _is_noise_frame(f.filename)]
    last = own_frames[-1] if own_frames else (te.stack[-1] if te.stack else None)

    hidden = 0 if full_stack else _trim_frames(te)

    error: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)}
    if last is not None:
        error["location"] = f"{_short_path(last.filename)}:{last.lineno} in {last.name}"
    stack = "".join(te.format())
    if hidden:
        stack = f"({hidden} library frames hidden)\n" + stack
    error["stack"] = redact_text(stack)
    return error


class RedactingJsonFormatter(logging.Formatter):
    """Formats a LogRecord as one JSON object, redacting all text in it."""

    def __init__(self, full_stack: bool = False) -> None:
        super().__init__()
        self.full_stack = full_stack

    def format(self, record: logging.LogRecord) -> str:
        try:
            message = record.getMessage()
        except Exception:  # bad %-format args must never crash logging
            message = f"{record.msg} {record.args}"

        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": _LEVEL_NAMES.get(record.levelname, record.levelname),
            "logger": record.name,
            "message": message,
            "service": SERVICE_NAME,
        }

        request_id = getattr(record, "request_id", None) or request_id_var.get()
        if request_id:
            entry["request_id"] = request_id

        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and key != "request_id" and not key.startswith("_"):
                entry[key] = value

        # Error traces: short stack (our code only) + exact location, all redacted.
        if record.exc_info and record.exc_info[1] is not None:
            entry["error"] = _format_error(record.exc_info[1], self.full_stack)
        if record.stack_info:
            entry["stack_info"] = record.stack_info

        # Single choke point: everything above (keys, message, extras, error) is redacted here.
        redacted = redact_data(entry)
        return json.dumps(redacted, default=_safe_default, ensure_ascii=False)


class _StdoutHandler(logging.StreamHandler):
    """Writes to whatever sys.stdout is *now* (lets pytest's capsys capture it)."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property  # type: ignore[override]
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value) -> None:
        pass


def _resolve_level(value: str | None) -> int:
    name = (value or "INFO").strip().upper()
    if name == "WARN":
        name = "WARNING"
    if name not in _VALID_LEVELS:
        raise ValueError(f"Invalid LOG_LEVEL {value!r}; use DEBUG, INFO, WARN, ERROR or CRITICAL")
    return getattr(logging, name)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def configure_logging(
    level: str | None = None,
    log_file: str | None = None,
    full_stack: bool | None = None,
) -> None:
    """Install the redacting JSON handlers on the root logger. Safe to call more than once."""
    level_no = _resolve_level(level if level is not None else os.getenv("LOG_LEVEL"))
    log_file = log_file if log_file is not None else os.getenv("LOG_FILE")
    full_stack = full_stack if full_stack is not None else _env_flag("LOG_FULL_STACK")

    formatter = RedactingJsonFormatter(full_stack=full_stack)
    handlers: list[logging.Handler] = [_StdoutHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    root = logging.getLogger()
    for old in root.handlers[:]:
        root.removeHandler(old)
        old.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level_no)

    # Uvicorn installs its own plain-text handlers; its error logger prints full,
    # unredacted tracebacks. Route it through ours instead.
    for name in ("uvicorn", "uvicorn.error", "fastapi"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers.clear()
        lib_logger.propagate = True
    # Our middleware already logs every request (without query strings), so
    # silence Uvicorn's access log, which would print raw URLs.
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
    access.disabled = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


__all__ = [
    "REDACTED",
    "RedactingJsonFormatter",
    "configure_logging",
    "get_logger",
    "request_id_var",
]