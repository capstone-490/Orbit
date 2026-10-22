# No substantial AI-generated code
import os

os.environ.setdefault("DB_NAME", "orbit_test")
os.environ.setdefault("DB_USER", "orbit_user")
os.environ.setdefault("DB_PASSWORD", "orbit_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "6105")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
