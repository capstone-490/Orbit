import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# ensure the backend root (/app) is on sys.path so app.* imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Escape '%' as '%%' so ConfigParser doesn't crash on URL-encoded passwords
config.set_main_option(
    "sqlalchemy.url",
    settings.sqlalchemy_database_uri.replace("%", "%%"),
)

# populate this with SQLAlchemy Base.metadata if using ORM models.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sqlalchemy_database_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        settings.sqlalchemy_database_uri,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
