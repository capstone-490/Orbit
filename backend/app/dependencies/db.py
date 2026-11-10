import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# SQLAlchemy engine for FastAPI runtime & tests (connects as orbit_app)
engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_connection(user_id: str | None = None, user_type: str = "System"):

    conn = psycopg.connect(settings.psycopg_database_uri)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                set_config('audit.user_id', %s, true),
                set_config('audit.user_type', %s, true)
            """,
            (str(user_id) if user_id else '', user_type)
        )

    return conn


def get_admin_connection():
    """Privileged connection for migrations and test infrastructure."""
    return psycopg.connect(settings.admin_psycopg_database_uri)
