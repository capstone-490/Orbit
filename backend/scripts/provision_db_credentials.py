from psycopg import sql

from app.core.config import settings
from app.db.db import get_admin_connection

ALLOWED_ROLES = {"orbit_app", "orbit_test"}


def provision_credentials(
    username: str | None = None, password: str | None = None
) -> None:
    username = settings.DB_USER if username is None else username
    password = settings.DB_PASSWORD if password is None else password

    if username not in ALLOWED_ROLES:
        raise ValueError(f"Unexpected application database role: {username}")

    if not password:
        raise ValueError("DB_PASSWORD must not be empty")

    with get_admin_connection() as conn:
        exists = conn.execute(
            """
            SELECT 1
            FROM pg_roles
            WHERE rolname = %s
            """,
            (username,),
        ).fetchone()

        if not exists:
            raise RuntimeError(
                f"Database role {username!r} does not exist. "
                "Run Alembic migrations first."
            )

        conn.execute(
            sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                sql.Identifier(username),
                sql.Literal(password),
            )
        )

        conn.commit()

    print(f"Successfully provisioned credentials for {username}.")


if __name__ == "__main__":
    provision_credentials()
