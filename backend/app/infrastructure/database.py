from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def ensure_asyncpg_uri(uri: str) -> str:
    """
    Ensures any 'postgresql://' or 'postgresql+psycopg://' URI is normalized to
    'postgresql+asyncpg://' so SQLAlchemy's AsyncEngine always uses the asyncpg driver.
    """
    parts = urlsplit(uri)
    if parts.scheme in (
        "postgres",
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    ):
        return urlunsplit(
            (
                "postgresql+asyncpg",
                parts.netloc,
                parts.path,
                parts.query,
                parts.fragment,
            )
        )
    return uri


def build_async_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
) -> AsyncEngine:
    """Creates the shared SQLAlchemy 2.0 AsyncEngine connection pool."""
    async_uri = ensure_asyncpg_uri(database_url)
    return create_async_engine(
        async_uri,
        echo=echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


def build_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Creates the session factory used by SqlAlchemyUnitOfWork per request."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
