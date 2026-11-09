"""add follow-up discussion notes

Revision ID: c8d4e6f1a2b3
Revises: 7f2c1a9e4b6d
Create Date: 2026-11-09

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c8d4e6f1a2b3"
down_revision: str | Sequence[str] | None = "7f2c1a9e4b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE follow_ups
        ADD COLUMN IF NOT EXISTS discussion_notes TEXT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE follow_ups
        DROP COLUMN IF EXISTS discussion_notes
        """
    )
