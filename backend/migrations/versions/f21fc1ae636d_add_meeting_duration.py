"""add meeting duration

Revision ID: f21fc1ae636d
Revises: bdacab6a88f6
Create Date: 2026-11-07 21:19:49.250379

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f21fc1ae636d"
down_revision: str | Sequence[str] | None = "bdacab6a88f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meetings",
        sa.Column(
            "duration_minutes",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )

    op.create_check_constraint(
        "ck_meetings_duration_positive",
        "meetings",
        "duration_minutes > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_meetings_duration_positive",
        "meetings",
        type_="check",
    )

    op.drop_column("meetings", "duration_minutes")
