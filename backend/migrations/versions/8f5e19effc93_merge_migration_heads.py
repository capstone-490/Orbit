"""merge migration heads

Revision ID: 8f5e19effc93
Revises: 396579aa7849, bdacab6a88f6
Create Date: 2026-11-02 20:36:53.984383

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "8f5e19effc93"
down_revision: str | Sequence[str] | None = ("396579aa7849", "bdacab6a88f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
