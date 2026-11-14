# Below 50% AI-generated
import pytest

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import DBAPIError

@pytest.fixture
def audit_event(db_session):
    result = db_session.execute(
        text("""
            INSERT INTO audit_events (
                resource_type,
                resource_id,
                action_type,
                actor_type,
                actor_id,
                before_state,
                after_state
            )
            VALUES (
                'clients',
                '999999',
                'UPDATE',
                'System',
                NULL,
                '{"name": "Old Name"}'::jsonb,
                '{"name": "New Name"}'::jsonb
            )
            RETURNING id
        """)
    )

    event_id = result.scalar_one()
    db_session.flush()

    return event_id


def test_delete_audit_event_is_rejected(
    db_session,
    audit_event,
):
    with pytest.raises(DBAPIError) as exc:
        with db_session.begin_nested():
            db_session.execute(
                text("""
                    DELETE FROM audit_events
                    WHERE id = :event_id
                """),
                {"event_id": audit_event},
            )

    assert exc.value.orig.sqlstate == "42501"

    result = db_session.execute(
        text("""
            SELECT id
            FROM audit_events
            WHERE id = :event_id
        """),
        {"event_id": audit_event},
    )

    assert result.scalar_one_or_none() == audit_event


def test_update_audit_event_is_rejected(
    db_session,
    audit_event,
):
    with pytest.raises(DBAPIError) as exc:
        with db_session.begin_nested():
            db_session.execute(
                text("""
                    UPDATE audit_events
                    SET action_type = 'DELETE'
                    WHERE id = :event_id
                """),
                {"event_id": audit_event},
            )

    assert exc.value.orig.sqlstate == "42501"

    result = db_session.execute(
        text("""
            SELECT action_type
            FROM audit_events
            WHERE id = :event_id
        """),
        {"event_id": audit_event},
    )

    assert result.scalar_one() == "UPDATE"


def test_application_role_has_no_update_or_delete_permissions(
    db_session,
):
    result = db_session.execute(
        text("""
            SELECT
                has_table_privilege(
                    current_user,
                    'audit_events',
                    'UPDATE'
                ),
                has_table_privilege(
                    current_user,
                    'audit_events',
                    'DELETE'
                )
        """)
    )

    can_update, can_delete = result.one()

    assert can_update is False
    assert can_delete is False

def test_client_insert_creates_audit_event(db_session):
    db_session.execute(
        text("""
            SELECT
                set_config('audit.user_id', '123', true),
                set_config('audit.user_type', 'Advisor', true)
        """)
    )

    result = db_session.execute(
        text("""
            INSERT INTO clients (
                name,
                email,
                phone_number
            )
            VALUES (
                'Audit Test Client',
                'audit-test@example.com',
                '5551234567'
            )
            RETURNING id
        """)
    )

    client_id = result.scalar_one()

    event = db_session.execute(
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
        """),
        {"client_id": str(client_id)},
    ).mappings().one()

    assert event["resource_type"] == "clients"
    assert event["resource_id"] == str(client_id)
    assert event["action_type"] == "INSERT"
    assert event["actor_id"] == "123"
    assert event["actor_type"] == "Advisor"

    assert event["before_state"] == {}
    assert event["after_state"]["name"] == "Audit Test Client"


def test_client_insert_no_config_create_systes_user(db_session):
    result = db_session.execute(
        text("""
            INSERT INTO clients (
                name,
                email,
                phone_number
            )
            VALUES (
                'Audit Test Client',
                'audit-test@example.com',
                '5551234567'
            )
            RETURNING id
        """)
    )

    client_id = result.scalar_one()

    event = db_session.execute(
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
        """),
        {"client_id": str(client_id)},
    ).mappings().one()

    assert event["resource_type"] == "clients"
    assert event["resource_id"] == str(client_id)
    assert event["action_type"] == "INSERT"
    assert event["actor_id"] is None
    assert event["actor_type"] == "System"

    assert event["before_state"] == {}
    assert event["after_state"]["name"] == "Audit Test Client"

def test_client_insert_wrong_user_type(db_session):
    db_session.execute(
        text("""
            SELECT
                set_config('audit.user_id', '123', true),
                set_config('audit.user_type', 'advisor', true)
        """)
    )
    with pytest.raises(IntegrityError) as exc_info:
        result = db_session.execute(
            text("""
                INSERT INTO clients (
                    name,
                    email,
                    phone_number
                )
                VALUES (
                    'Audit Test Client',
                    'audit-test@example.com',
                    '5551234567'
                )
                RETURNING id
            """)
        )

    assert "audit_events_actor_type_check" in str(exc_info.value)



def test_client_update_creates_accurate_audit_diff(db_session):
    result = db_session.execute(
        text("""
            INSERT INTO clients (
                name,
                email,
                phone_number
            )
            VALUES (
                'Carrot',
                'potato@example.com',
                '1111111111'
            )
            RETURNING id
        """)
    )

    client_id = result.scalar_one()

    db_session.execute(
        text("""
            SELECT set_config('audit.user_id', '123', true),
                   set_config('audit.user_type', 'Advisor', true)
        """)
    )

    db_session.execute(
        text("""
            UPDATE clients
            SET name = 'Updated Name'
            WHERE id = :client_id
        """),
        {"client_id": client_id},
    )

    event = db_session.execute(
        text("""
            SELECT before_state, after_state
            FROM audit_events
            WHERE resource_type = 'clients'
              AND resource_id = :client_id
              AND action_type = 'UPDATE'
        """),
        {"client_id": str(client_id)},
    ).mappings().one()

    assert event["before_state"] == {
        "name": "Carrot"
    }

    assert event["after_state"] == {
        "name": "Updated Name"
    }


def test_audit_event_rolls_back_with_business_transaction(db_session):
    nested = db_session.begin_nested()

    try:
        client_id = db_session.execute(
            text("""
                INSERT INTO clients (
                    name,
                    email,
                    phone_number
                )
                VALUES (
                    'Rollback Client',
                    'rollback@example.com',
                    '5553333333'
                )
                RETURNING id
            """)
        ).scalar_one()

        event_id = db_session.execute(
            text("""
                SELECT id
                FROM audit_events
                WHERE resource_type = 'clients'
                  AND resource_id = :client_id
            """),
            {"client_id": str(client_id)},
        ).scalar_one()

        assert event_id is not None

    finally:
        nested.rollback()

    client_exists = db_session.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM clients WHERE id = :client_id
            )
        """),
        {"client_id": client_id},
    ).scalar_one()

    audit_exists = db_session.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM audit_events
                WHERE id = :event_id
            )
        """),
        {"event_id": event_id},
    ).scalar_one()

    assert client_exists is False
    assert audit_exists is False