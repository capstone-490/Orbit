# Below 50% AI-generated code
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database import build_async_engine, build_session_factory


@pytest.fixture(scope="function")
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
    """Async session factory wired to preset env vars / .env via settings."""
    # Uses DB_USER (orbit_app) so RLS policies and bypass_rls GUCs are properly tested.
    # Switch to settings.admin_database_uri if superuser privileges are needed.
    engine = build_async_engine(
        settings.sqlalchemy_database_uri.replace(
            "postgresql+psycopg", "postgresql+asyncpg"
        )
    )
    factory = build_session_factory(engine)
    yield factory
    await engine.dispose()


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
