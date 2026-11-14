"""add meeting duration

Revision ID: f21fc1ae636d
Revises: bdacab6a88f6
Create Date: 2026-11-07 21:19:49.250379

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f21fc1ae636d"
down_revision: str | Sequence[str] | None = "bdacab6a88f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE meetings
        ADD COLUMN IF NOT EXISTS duration_minutes INTEGER NOT NULL DEFAULT 30;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_meetings_duration_positive'
                  AND conrelid = 'meetings'::regclass
            ) THEN
                ALTER TABLE meetings
                ADD CONSTRAINT ck_meetings_duration_positive
                CHECK (duration_minutes > 0);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_constraint(
        "ck_meetings_duration_positive",
        "meetings",
        type_="check",
    )

    op.drop_column("meetings", "duration_minutes")
