"""add client financial summaries

Revision ID: d2e83f1a4c7b
Revises: 8f5e19effc93
Create Date: 2026-11-15

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e83f1a4c7b"
down_revision: str | Sequence[str] | None = "8f5e19effc93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE t_client_financial_summaries (
            client_id BIGINT PRIMARY KEY
                REFERENCES t_clients(id) ON DELETE CASCADE,
            annual_income NUMERIC(14, 2)
                CHECK (annual_income IS NULL OR annual_income >= 0),
            risk_tolerance TEXT
                CHECK (risk_tolerance IS NULL OR risk_tolerance IN (
                    'Conservative', 'Moderate', 'Aggressive'
                )),
            target_retirement_age SMALLINT
                CHECK (target_retirement_age IS NULL
                       OR target_retirement_age BETWEEN 0 AND 130),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE t_client_financial_summaries;")
