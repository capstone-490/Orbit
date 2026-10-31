
import io
import json
import sys
from contextlib import redirect_stdout

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_config import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers.debug import router as debug_router

FAKE_CLIENT = {"email": "jane.doe@example.com", "sin": "046-454-286", "phone": "514-555-0198"}

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
app.include_router(debug_router)

print("\n========== REQUEST (synthetic client, missing 'name') ==========")
print("POST /debug/clients", json.dumps(FAKE_CLIENT))

captured = io.StringIO()
with redirect_stdout(captured):
    configure_logging(level="INFO", log_file="")
    response = TestClient(app).post("/debug/clients", json=FAKE_CLIENT)

print("\n========== RESPONSE ==========")
print("Status:", response.status_code)
print("x-request-id:", response.headers["x-request-id"])
print("Body:", response.text)

print("\n========== LOG STREAM (app lines, stack trace shortened) ==========")
for line in captured.getvalue().splitlines():
    entry = json.loads(line)
    if not entry["logger"].startswith("app"):
        continue
    if "error" in entry:
        stack = entry["error"]["stack"].strip().splitlines()
        entry["error"]["stack"] = ["..."] + stack[-3:]
    print(json.dumps(entry, indent=2))

leaks = [value for value in FAKE_CLIENT.values() if value in captured.getvalue()]
print("\n========== RESULT ==========")
print("PII found in logs:", leaks or "none")
print("Request id on every app line:", all(
    json.loads(l).get("request_id") == response.headers["x-request-id"]
    for l in captured.getvalue().splitlines()
    if json.loads(l)["logger"].startswith("app")
))
sys.exit(1 if leaks else 0)