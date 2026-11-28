"""add financial goals

Revision ID: 901dc549fcb1
Revises: 8f5e19effc93
Create Date: 2026-11-28 01:01:49.956014

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "901dc549fcb1"
down_revision: str | Sequence[str] | None = "8f5e19effc93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add category to existing client goals.
    op.execute("""
        ALTER TABLE public.t_goals
        ADD COLUMN category TEXT;
    """)

    # Create reference table for predefined financial goals.
    op.execute("""
        CREATE TABLE public.goal_types (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            duration goal_duration NOT NULL,
            category TEXT NOT NULL
        );
    """)

    # Seed predefined financial goals.
    op.execute("""
        INSERT INTO public.goal_types
            (code, name, duration, category)
        VALUES
            (
                'emergency_fund',
                'Build Savings for Unexpected Expenses',
                'Short-term',
                'Emergency Fund'
            ),
            (
                'debt_payoff',
                'Pay Off Credit Cards / Debts',
                'Short-term',
                'Debt Payoff'
            ),
            (
                'major_purchase',
                'Make a Major Purchase',
                'Short-term',
                'Cash Flow'
            ),
            (
                'buy_home',
                'Buy a New Home',
                'Medium-term',
                'Real Estate'
            ),
            (
                'mortgage_payoff',
                'Reduce or Pay Off Mortgage',
                'Medium-term',
                'Equity Goal'
            ),
            (
                'alternative_income',
                'Alternative Income (Disability / Death Protection)',
                'Medium-term',
                'Insurance'
            ),
            (
                'retirement',
                'Build Retirement Wealth',
                'Long-term',
                'Core Target'
            ),
            (
                'education',
                'Education Funding',
                'Long-term',
                '529 College'
            ),
            (
                'aging_parents',
                'Help Support Aging Parents',
                'Long-term',
                'Family Trust'
            ),
            (
                'legacy_estate',
                'Other Horizon Goals',
                'Long-term',
                'Legacy / Estate'
            );
    """)

    # Predefined goal types are read-only for application roles.
    for role in ("orbit_app", "orbit_test"):
        op.execute(f"""
            REVOKE ALL PRIVILEGES
            ON TABLE public.goal_types
            FROM {role};
        """)

        op.execute(f"""
            GRANT SELECT
            ON TABLE public.goal_types
            TO {role};
        """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE public.goal_types;
    """)

    op.execute("""
        ALTER TABLE public.t_goals
        DROP COLUMN category;
    """)
