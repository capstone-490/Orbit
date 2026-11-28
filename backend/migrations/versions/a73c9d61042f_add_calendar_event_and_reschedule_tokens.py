"""add calendar event and reschedule tokens

Revision ID: a73c9d61042f
Revises: 8f5e19effc93
Create Date: 2026-11-27

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a73c9d61042f"
down_revision: str | Sequence[str] | None = "8f5e19effc93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE t_meetings
        ADD COLUMN google_calendar_id TEXT,
        ADD COLUMN google_event_id TEXT,
        ADD COLUMN reschedule_token_hash TEXT UNIQUE;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE t_meetings
        DROP COLUMN reschedule_token_hash,
        DROP COLUMN google_event_id,
        DROP COLUMN google_calendar_id;
    """)
