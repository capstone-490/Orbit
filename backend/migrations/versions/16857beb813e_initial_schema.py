"""initial schema

Revision ID: 16857beb813e
Revises:
Create Date: 2026-10-24 22:13:58.534889

"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

# revision identifiers, used by alembic.
revision: str = "16857beb813e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def upgrade() -> None:
    sql = (SQL_DIR / "01_base_schema.sql").read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    raise NotImplementedError("Initial schema downgrade requires an explicit policy.")
