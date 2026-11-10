"""add google meet columns and google oauth credentials

Revision ID: c4f1a2b9d7e3
Revises: bdacab6a88f6
Create Date: 2026-11-08 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f1a2b9d7e3"
down_revision: str | Sequence[str] | None = "bdacab6a88f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Google Meet link and code (e.g. abc-defg-hij); NULL when not a Google Meet
    op.execute("""
        ALTER TABLE meetings
            ADD COLUMN IF NOT EXISTS meeting_uri TEXT,
            ADD COLUMN IF NOT EXISTS meeting_code TEXT;
    """)

    # One Google account per advisor. credentials holds Credentials.to_json()
    # encrypted with GOOGLE_TOKEN_ENCRYPTION_KEY (Fernet), never plain text.
    # calendar_id is the secondary calendar Orbit creates for meetings; NULL
    # until the first meeting is scheduled.
    op.execute("""
        CREATE TABLE IF NOT EXISTS google_oauth_credentials (
            advisor_id BIGINT PRIMARY KEY,
            credentials TEXT NOT NULL,
            calendar_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_google_oauth_credentials_advisor
                FOREIGN KEY (advisor_id)
                REFERENCES advisors(id)
                ON DELETE CASCADE
        );
    """)

    op.execute("""
        CREATE TRIGGER trg_google_oauth_credentials_updated_at
        BEFORE UPDATE ON google_oauth_credentials
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS google_oauth_credentials;")
    op.execute("""
        ALTER TABLE meetings
            DROP COLUMN IF EXISTS meeting_code,
            DROP COLUMN IF EXISTS meeting_uri;
    """)
