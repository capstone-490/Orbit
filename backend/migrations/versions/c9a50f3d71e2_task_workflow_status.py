"""Replace task completion boolean with workflow status.

Revision ID: c9a50f3d71e2
Revises: bdacab6a88f6
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a50f3d71e2"
down_revision: str | Sequence[str] | None = "bdacab6a88f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'tasks'
                  AND column_name = 'status'
            ) THEN
                ALTER TABLE tasks ADD COLUMN status VARCHAR(16);

                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'tasks'
                      AND column_name = 'completed'
                ) THEN
                    UPDATE tasks
                    SET status = CASE
                        WHEN COALESCE(completed, FALSE) THEN 'COMPLETED'
                        ELSE 'TO_DO'
                    END;
                ELSE
                    UPDATE tasks SET status = 'TO_DO';
                END IF;
            END IF;
        END
        $$;

        UPDATE tasks SET status = 'TO_DO' WHERE status IS NULL;

        ALTER TABLE tasks
        ALTER COLUMN status SET DEFAULT 'TO_DO',
        ALTER COLUMN status SET NOT NULL;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_tasks_status'
                  AND conrelid = 'tasks'::regclass
            ) THEN
                ALTER TABLE tasks
                ADD CONSTRAINT ck_tasks_status
                CHECK (status IN ('TO_DO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED'));
            END IF;
        END
        $$;

        ALTER TABLE tasks DROP COLUMN IF EXISTS completed;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE tasks
        ADD COLUMN completed BOOLEAN NOT NULL DEFAULT FALSE;

        UPDATE tasks
        SET completed = (status = 'COMPLETED');

        ALTER TABLE tasks DROP CONSTRAINT ck_tasks_status;
        ALTER TABLE tasks DROP COLUMN status;
    """)
