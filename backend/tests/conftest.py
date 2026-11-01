# No substantial AI-generated code
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.deps import get_db
from app.main import app


@pytest.fixture(scope="session")
def db_engine():
    """Single engine connection to the already-migrated & seeded test DB."""

    engine = create_engine(
        settings.sqlalchemy_database_uri,
        pool_pre_ping=True,
    )

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient wired to the isolated per-test database session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
