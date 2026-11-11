# No substantial AI-generated code

pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.auth",
]

from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from app.dependencies.deps import get_db
from app.main import create_application

DEFAULT_API_VERSION = "v1"


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
def api_client(app):
    """Factory fixture to spawn TestClients for any API version or headers."""
    with ExitStack() as stack:

        def _make_client(version: str = DEFAULT_API_VERSION, **kwargs) -> TestClient:
            return stack.enter_context(
                TestClient(
                    app,
                    base_url=f"http://testserver/api/{version}",
                    **kwargs,
                )
            )

        yield _make_client


@pytest.fixture
def client(api_client, request):
    """Default client using DEFAULT_API_VERSION (supports indirect parametrize)."""
    version = getattr(request, "param", DEFAULT_API_VERSION)
    return api_client(version)


@pytest.fixture
def client_v1(api_client):
    return api_client("v1")


@pytest.fixture
def client_v2(api_client):
    return api_client("v2")
