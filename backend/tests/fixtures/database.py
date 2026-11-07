import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        settings.sqlalchemy_database_uri,
        pool_pre_ping=True,
    )

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
