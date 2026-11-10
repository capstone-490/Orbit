# No substantial AI-generated code

pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.auth",
]


import pytest
from fastapi.testclient import TestClient

from app.dependencies.deps import get_db
from app.main import create_application


@pytest.fixture
def app(db_session):
    application = create_application()

    original_overrides = application.dependency_overrides.copy()

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    yield application

    application.dependency_overrides.clear()
    application.dependency_overrides.update(original_overrides)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
