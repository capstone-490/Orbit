"""merge meeting and follow-up migration heads

Revision ID: b5625ed64498
Revises: f21fc1ae636d, c8d4e6f1a2b3
Create Date: 2026-11-10 00:52:43.899058

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b5625ed64498"
down_revision: str | Sequence[str] | None = ("f21fc1ae636d", "c8d4e6f1a2b3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
