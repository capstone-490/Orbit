# 50% or more AI-generated
import json
import logging
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.logging_config import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers.debug import router as debug_router

FAKE_EMAIL = "jane.doe@example.com"
FAKE_SIN = "046-454-286"
FAKE_PHONE = "514-555-0198"


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(debug_router)

    @app.get("/ok")
    def ok():
        logging.getLogger("app.test").info("Inside handler")
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError(f"Could not email {FAKE_EMAIL}")

    @app.get("/not-found")
    def not_found():
        raise HTTPException(status_code=404, detail="nope")

    return app


@pytest.fixture
def logs(capsys):
    """Configure logging, then return a function that parses captured stdout as JSON lines."""
    configure_logging(level="DEBUG", log_file="", full_stack=False)

    def read(app_only: bool = True):
        out = capsys.readouterr().out
        entries = [json.loads(line) for line in out.splitlines() if line.strip()]
        if app_only:  # drop the test client's own lines (httpx, asyncio)
            entries = [e for e in entries if e["logger"].startswith("app")]
        return entries, out

    return read


@pytest.fixture
def client():
    return TestClient(build_app())


# ---- Story testing plan ---------------------------------------------------


def test_exception_with_email_is_redacted_and_has_request_id(client, logs):
    response = client.get("/boom")
    entries, raw = logs()

    assert response.status_code == 500
    request_id = response.headers["x-request-id"]
    assert uuid.UUID(request_id)

    assert FAKE_EMAIL not in raw  # nothing anywhere in stdout leaks it
    error_entry = next(e for e in entries if "error" in e)
    assert error_entry["level"] == "ERROR"
    assert error_entry["request_id"] == request_id
    assert "[REDACTED]" in error_entry["error"]["message"]
    assert "[REDACTED]" in error_entry["error"]["stack"]
    assert "RuntimeError" in error_entry["error"]["stack"]


def test_demo_post_with_sin_returns_500_and_redacts_everything(client, logs):
    payload = {"email": FAKE_EMAIL, "sin": FAKE_SIN, "phone": FAKE_PHONE}
    response = client.post("/debug/clients", json=payload)
    entries, raw = logs()

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal Server Error",
        "request_id": response.headers["x-request-id"],
    }
    for secret in (FAKE_EMAIL, FAKE_SIN, FAKE_PHONE):
        assert secret not in raw
        assert secret not in response.text
    # every line written during the request carries the same id
    assert {e.get("request_id") for e in entries} == {response.headers["x-request-id"]}


# ---- Acceptance criteria --------------------------------------------------


def test_every_line_is_json_with_required_fields(client, logs):
    client.get("/ok")
    all_entries, raw = logs(
        app_only=False
    )  # json.loads already proved every line is JSON
    assert len(all_entries) == len(raw.strip().splitlines())
    for entry in all_entries:
        for field in ("timestamp", "level", "logger", "message", "service"):
            assert field in entry
    entries = [e for e in all_entries if e["logger"].startswith("app")]
    assert entries
    for entry in entries:
        for field in (
            "timestamp",
            "level",
            "logger",
            "message",
            "service",
            "request_id",
        ):
            assert field in entry


def test_request_log_has_path_status_and_request_id(client, logs):
    response = client.get("/ok", params={"email": FAKE_EMAIL})
    entries, raw = logs()

    access = next(e for e in entries if e["message"] == "Request completed")
    assert access["method"] == "GET"
    assert access["path"] == "/ok"  # no query string
    assert access["status_code"] == 200
    assert access["level"] == "INFO"
    assert isinstance(access["duration_ms"], float)
    assert access["request_id"] == response.headers["x-request-id"]
    assert FAKE_EMAIL not in raw


def test_handler_logs_inherit_request_id(client, logs):
    response = client.get("/ok")
    entries, _ = logs()
    handler_entry = next(e for e in entries if e["message"] == "Inside handler")
    assert handler_entry["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    "path,status,level",
    [("/ok", 200, "INFO"), ("/not-found", 404, "WARN"), ("/boom", 500, "ERROR")],
)
def test_level_follows_status_code(client, logs, path, status, level):
    client.get(path)
    entries, _ = logs()
    access = next(e for e in entries if e["message"] == "Request completed")
    assert access["status_code"] == status
    assert access["level"] == level


def test_valid_incoming_request_id_is_reused(client, logs):
    incoming = str(uuid.uuid4())
    response = client.get("/ok", headers={"x-request-id": incoming})
    entries, _ = logs()
    assert response.headers["x-request-id"] == incoming
    assert all(e["request_id"] == incoming for e in entries)


def test_invalid_incoming_request_id_is_replaced(client, logs):
    response = client.get("/ok", headers={"x-request-id": FAKE_EMAIL})
    _, raw = logs()
    assert response.headers["x-request-id"] != FAKE_EMAIL
    assert uuid.UUID(response.headers["x-request-id"])
    assert FAKE_EMAIL not in raw


@pytest.mark.parametrize(
    "env_value,debug_shown,info_shown,warn_shown",
    [
        ("DEBUG", True, True, True),
        ("INFO", False, True, True),
        ("WARN", False, False, True),
        ("ERROR", False, False, False),
    ],
)
def test_log_level_comes_from_environment(
    monkeypatch, capsys, env_value, debug_shown, info_shown, warn_shown
):
    monkeypatch.setenv("LOG_LEVEL", env_value)
    configure_logging(log_file="")
    log = logging.getLogger("app.level-test")
    log.debug("d-line")
    log.info("i-line")
    log.warning("w-line")
    out = capsys.readouterr().out
    assert ("d-line" in out) is debug_shown
    assert ("i-line" in out) is info_shown
    assert ("w-line" in out) is warn_shown


def test_invalid_log_level_fails_fast():
    with pytest.raises(ValueError):
        configure_logging(level="LOUD", log_file="")


def test_log_file_receives_redacted_json(tmp_path, capsys):
    log_path = tmp_path / "app.log"
    configure_logging(level="INFO", log_file=str(log_path))
    logging.getLogger("app.file-test").error("Failed for %s", FAKE_EMAIL)
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert FAKE_EMAIL not in content
    assert json.loads(content.splitlines()[-1])["message"] == "Failed for [REDACTED]"
    configure_logging(level="INFO", log_file="")  # release the file handle


# ---- Error logs cannot bypass redaction ------------------------------------


def test_logger_exception_outside_requests_is_redacted(logs):
    try:
        raise ValueError(f"SIN {FAKE_SIN} rejected")
    except ValueError:
        logging.getLogger("app.worker").exception(
            "Background job failed for %s", FAKE_EMAIL
        )
    entries, raw = logs()
    assert FAKE_SIN not in raw and FAKE_EMAIL not in raw
    assert entries[0]["message"] == "Background job failed for [REDACTED]"
    assert "request_id" not in entries[0]


def test_chained_exception_cause_is_redacted(logs):
    try:
        try:
            raise KeyError(FAKE_PHONE)
        except KeyError as inner:
            raise RuntimeError("Lookup failed") from inner
    except RuntimeError:
        logging.getLogger("app.worker").exception("Chained failure")
    _, raw = logs()
    assert FAKE_PHONE not in raw


def test_extra_fields_and_keys_are_redacted(logs):
    logging.getLogger("app.test").warning(
        "Client update",
        extra={
            "client": {"email": FAKE_EMAIL, "notes": [f"call {FAKE_PHONE}"]},
            FAKE_SIN: "as key",
        },
    )
    entries, raw = logs()
    assert FAKE_EMAIL not in raw and FAKE_PHONE not in raw and FAKE_SIN not in raw
    assert entries[0]["client"]["email"] == "[REDACTED]"


def test_non_json_objects_are_stringified_then_redacted(logs):
    class Client:
        def __str__(self):
            return f"Client<{FAKE_EMAIL}>"

    logging.getLogger("app.test").info(
        "Saved", extra={"obj": Client(), "ids": {uuid.uuid4()}}
    )
    _, raw = logs()
    assert FAKE_EMAIL not in raw
    assert "Client<[REDACTED]>" in raw


def test_exception_passed_as_log_argument_is_redacted(logs):
    err = ValueError(f"bad email {FAKE_EMAIL}")
    logging.getLogger("app.test").error("Failure: %s", err, extra={"err": err})
    _, raw = logs()
    assert FAKE_EMAIL not in raw


def test_uvicorn_error_logger_goes_through_redaction(logs):
    logging.getLogger("uvicorn.error").error(
        "Exception in ASGI application for %s", FAKE_EMAIL
    )
    entries, raw = logs(app_only=False)
    assert FAKE_EMAIL not in raw
    assert entries[0]["logger"] == "uvicorn.error"


def test_error_stack_is_short_and_points_to_our_code(client, logs):
    client.post("/debug/clients", json={"email": FAKE_EMAIL})
    entries, _ = logs()
    error = next(e for e in entries if "error" in e)["error"]

    assert "site-packages" not in error["stack"]
    assert "library frames hidden" in error["stack"]
    assert error["location"].endswith("in create_client_demo")
    assert "debug.py" in error["location"]
    assert error["stack"].count("\n") < 10
    assert FAKE_EMAIL not in json.dumps(error)


def test_full_stack_switch_keeps_library_frames_and_still_redacts(
    monkeypatch, capsys, client
):
    monkeypatch.setenv("LOG_FULL_STACK", "true")
    configure_logging(
        level="INFO", log_file=""
    )  # reads LOG_FULL_STACK from the environment

    client.post("/debug/clients", json={"email": FAKE_EMAIL, "sin": FAKE_SIN})
    out = capsys.readouterr().out
    entries = [json.loads(line) for line in out.splitlines() if line.strip()]
    error = next(e for e in entries if "error" in e)["error"]

    assert "site-packages" in error["stack"]  # library frames are back
    assert "library frames hidden" not in error["stack"]
    assert "debug.py" in error["location"]  # location still points at our code
    assert FAKE_EMAIL not in out and FAKE_SIN not in out  # still redacted

    configure_logging(level="INFO", log_file="", full_stack=False)


def test_chained_exception_keeps_both_errors_in_short_stack(logs):
    try:
        try:
            raise KeyError(FAKE_PHONE)
        except KeyError as inner:
            raise RuntimeError("Lookup failed") from inner
    except RuntimeError:
        logging.getLogger("app.worker").exception("Chained failure")
    entries, raw = logs()
    stack = entries[0]["error"]["stack"]
    assert "KeyError" in stack and "RuntimeError" in stack
    assert FAKE_PHONE not in raw


def test_non_pii_content_is_preserved(logs):
    logging.getLogger("app.test").info(
        "Client status: Active", extra={"client_id": 42, "active": True}
    )
    entries, _ = logs()
    assert entries[0]["message"] == "Client status: Active"
    assert entries[0]["client_id"] == 42 and entries[0]["active"] is True
