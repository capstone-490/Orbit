"""merge google meet and task status migration heads

Revision ID: f6a8c0d2e4b7
Revises: c4f1a2b9d7e3, e2b4c6d8f0a1
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f6a8c0d2e4b7"
down_revision: str | Sequence[str] | None = ("c4f1a2b9d7e3", "e2b4c6d8f0a1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
