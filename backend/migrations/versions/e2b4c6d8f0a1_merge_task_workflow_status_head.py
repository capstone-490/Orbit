"""merge task workflow status migration head

Revision ID: e2b4c6d8f0a1
Revises: b5625ed64498, c9a50f3d71e2
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "e2b4c6d8f0a1"
down_revision: str | Sequence[str] | None = ("b5625ed64498", "c9a50f3d71e2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
