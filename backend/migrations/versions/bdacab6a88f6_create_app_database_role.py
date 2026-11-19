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
    # Ensure the migration role owning SECURITY DEFINER triggers
    # can bypass FORCE ROW LEVEL SECURITY on audit_events.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = current_user
                  AND (rolsuper OR rolbypassrls)
            ) THEN
                RAISE EXCEPTION
                    'Migration role % must have SUPERUSER or BYPASSRLS for SECURITY DEFINER audit_trigger()',
                    current_user;
            END IF;
        END
        $$;
    """)

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
                    EXECUTE format('CREATE ROLE %I', role_name);
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

    # Harden SECURITY DEFINER trigger function: triggers still fire for app roles
    # without needing direct EXECUTE privileges.
    op.execute("""
        REVOKE ALL ON FUNCTION public.audit_trigger() FROM PUBLIC;
    """)

    # Existing tables.
    for role in ROLES:
        op.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA public
            TO {role};
        """)

        # audit_events is append-only; app roles can read and insert app-level
        # audit events (subject to RLS), but never mutate or delete.
        op.execute(f"""
            REVOKE UPDATE, DELETE, TRUNCATE
            ON TABLE public.audit_events
            FROM {role};
        """)

        op.execute(f"""
            GRANT SELECT, INSERT
            ON TABLE public.audit_events
            TO {role};
        """)

        op.execute(f"""
            GRANT USAGE, SELECT, UPDATE
            ON ALL SEQUENCES IN SCHEMA public
            TO {role};
        """)

        op.execute(f"""
            GRANT EXECUTE ON FUNCTION
                public.current_tenant_org_id(),
                public.is_rls_bypassed()
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
            ALTER DEFAULT PRIVILEGES
            IN SCHEMA public
            REVOKE ALL ON TABLES
            FROM {role};
        """)

        op.execute(f"""
            ALTER DEFAULT PRIVILEGES
            IN SCHEMA public
            REVOKE ALL ON SEQUENCES
            FROM {role};
        """)

        op.execute(f"""
            REVOKE EXECUTE ON FUNCTION
                public.current_tenant_org_id(),
                public.is_rls_bypassed()
            FROM {role};
        """)

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
