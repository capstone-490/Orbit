"""create app database role

Revision ID: bdacab6a88f6
Revises: 16857beb813e
Create Date: 2026-10-31 21:28:23.515694

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdacab6a88f6"
down_revision: str | Sequence[str] | None = "16857beb813e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLES = ("orbit_app", "orbit_test")


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            role_name TEXT;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['orbit_app', 'orbit_test']
            LOOP
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_roles
                    WHERE rolname = role_name
                ) THEN
                    EXECUTE format(
                        'CREATE ROLE %I',
                        role_name
                    );
                END IF;

                EXECUTE format(
                    'ALTER ROLE %I
                     WITH LOGIN
                     NOSUPERUSER
                     NOCREATEDB
                     NOCREATEROLE
                     NOREPLICATION
                     NOBYPASSRLS',
                    role_name
                );
            END LOOP;
        END
        $$;
    """)

    # Database and schema access.
    op.execute("""
        DO $$
        DECLARE
            role_name TEXT;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['orbit_app', 'orbit_test']
            LOOP
                EXECUTE format(
                    'GRANT CONNECT ON DATABASE %I TO %I',
                    current_database(),
                    role_name
                );

                EXECUTE format(
                    'GRANT USAGE ON SCHEMA public TO %I',
                    role_name
                );
            END LOOP;
        END
        $$;
    """)

    # Existing tables.
    for role in ROLES:
        op.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA public
            TO {role};
        """)

        op.execute(f"""
            REVOKE UPDATE, DELETE, TRUNCATE
            ON TABLE audit_log
            FROM {role};
        """)

        op.execute(f"""
            GRANT SELECT, INSERT
            ON TABLE audit_log
            TO {role};
        """)

        op.execute(f"""
            GRANT USAGE, SELECT, UPDATE
            ON ALL SEQUENCES IN SCHEMA public
            TO {role};
        """)

        # Future tables and sequences created by the migration owner.
        op.execute(f"""
            ALTER DEFAULT PRIVILEGES
            IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE
            ON TABLES TO {role};
        """)

        op.execute(f"""
            ALTER DEFAULT PRIVILEGES
            IN SCHEMA public
            GRANT USAGE, SELECT, UPDATE
            ON SEQUENCES TO {role};
        """)


def downgrade() -> None:
    # Do not DROP ROLE or DROP OWNED here.
    for role in ROLES:
        op.execute(f"""
            REVOKE ALL PRIVILEGES
            ON ALL TABLES IN SCHEMA public
            FROM {role};
        """)

        op.execute(f"""
            REVOKE ALL PRIVILEGES
            ON ALL SEQUENCES IN SCHEMA public
            FROM {role};
        """)

        op.execute(f"""
            REVOKE USAGE
            ON SCHEMA public
            FROM {role};
        """)

        op.execute("""
        DO $$
        DECLARE
            role_name TEXT;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['orbit_app', 'orbit_test']
            LOOP
                EXECUTE format(
                    'REVOKE CONNECT ON DATABASE %I FROM %I',
                    current_database(),
                    role_name
                );
            END LOOP;
        END
        $$;
    """)
