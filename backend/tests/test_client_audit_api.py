# Below 50% AI-generated
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text

from app.auth import create_access_token
from app.core.config import settings


@pytest.fixture
def existing_advisor():
    """Create a committed advisor for testing."""

    email = f"test_advisor_{uuid4().hex[:8]}@example.com"

    with psycopg.connect(settings.psycopg_database_uri) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO advisors (
                    username,
                    email,
                    password_hash
                )
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                ("test_advisor", email, "test_password_hash"),
            )
            advisor_id = cur.fetchone()[0]

    yield {"id": advisor_id}

    with psycopg.connect(settings.psycopg_database_uri) as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM advisors WHERE id = %s",
                (advisor_id,),
            )


@pytest.fixture
def advisor_auth_headers(existing_advisor):
    """Generate authentication headers for the test advisor."""

    token = create_access_token(existing_advisor["id"])

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def existing_client(existing_advisor):
    """Create a committed client associated with the advisor."""

    email = f"test_client_{uuid4().hex[:8]}@example.com"
    phone = f"555{uuid4().int % 10**7:07d}"

    with psycopg.connect(settings.psycopg_database_uri) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (
                    name,
                    phone_number,
                    email,
                    advisor_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, name
                """,
                (
                    "Original Client",
                    phone,
                    email,
                    existing_advisor["id"],
                ),
            )

            result = cur.fetchone()

    client_record = {
        "id": result[0],
        "name": result[1],
    }

    yield client_record

    with psycopg.connect(settings.psycopg_database_uri) as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM clients WHERE id = %s",
                (client_record["id"],),
            )


def test_patch_client_creates_exactly_one_audit_event(
    client,
    db_session,
    advisor_auth_headers,
    existing_client,
):
    client_id = existing_client["id"]

    initial_count = db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM audit_events
            WHERE resource_type = 'clients'
              AND resource_id = :client_id
        """),
        {"client_id": str(client_id)},
    ).scalar_one()

    response = client.patch(
        f"/clients/{client_id}",
        json={"name": "Updated Client Name"},
        headers=advisor_auth_headers,
    )

    assert response.status_code == 200, response.text

    events = (
        db_session.execute(
            text("""
            SELECT
                resource_type,
                resource_id,
                action_type,
                actor_id,
                actor_type,
                before_state,
                after_state
            FROM audit_events
            WHERE resource_type = 'clients'
              AND resource_id = :client_id
            ORDER BY changed_at DESC
        """),
            {"client_id": str(client_id)},
        )
        .mappings()
        .all()
    )

    assert len(events) == initial_count + 1

    event = events[0]

    assert event["resource_type"] == "clients"
    assert event["resource_id"] == str(client_id)
    assert event["action_type"] == "UPDATE"
    assert event["actor_type"] == "Advisor"

    assert event["before_state"]["name"] == existing_client["name"]
    assert event["after_state"]["name"] == "Updated Client Name"