# Substantial AI assistance used; verified with backend tests and live auth smoke test.
import os

os.environ.setdefault("DB_NAME", "orbit_test")
os.environ.setdefault("DB_USER", "orbit_user")
os.environ.setdefault("DB_PASSWORD", "orbit_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "6105")
os.environ.setdefault("ORBIT_AUTH_SECRET", "test-secret-with-at-least-32-bytes")
os.environ.setdefault(
    "ORBIT_ANONYMIZATION_SECRET",
    "test-only-anonymization-secret-with-32-chars",
)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import create_access_token


@pytest.fixture
def client():
    headers = {"Authorization": f"Bearer {create_access_token(1)}"}
    with TestClient(app, headers=headers) as test_client:
        yield test_client
