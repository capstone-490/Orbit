# Below 50% AI-generated
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


@pytest.fixture
def tenant_context(db_session):
    """Creates a minimal tenant hierarchy (identity -> org -> subscription) and sets RLS context."""
    db_session.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))

    identity_id = db_session.execute(
        text("""
            INSERT INTO identities (issuer, subject, email)
            VALUES ('https://auth.example.com', gen_random_uuid()::text, 'owner@example.com')
            RETURNING id
        """)
    ).scalar_one()

    org_id = db_session.execute(
        text("""
            INSERT INTO organizations (name, owner_identity_id, status)
            VALUES ('Test Org', :identity_id, 'provisioning')
            RETURNING id
        """),
        {"identity_id": identity_id},
    ).scalar_one()

    sub_id = db_session.execute(
        text("""
            INSERT INTO subscriptions (organization_id, name, purpose, is_default, status)
            VALUES (:org_id, 'Default Sub', 'default', TRUE, 'active')
            RETURNING id
        """),
        {"org_id": org_id},
    ).scalar_one()

    # Clear audit events generated during fixture setup and scope session to tenant
    db_session.execute(
        text("""
            SELECT
                set_config('app.bypass_rls', 'off', true),
                set_config('app.current_org_id', :org_id, true),
                set_config('audit.user_id', '', true),
                set_config('audit.user_type', '', true)
        """),
        {"org_id": str(org_id)},
    )
    db_session.flush()

    return {"org_id": org_id, "sub_id": sub_id, "identity_id": identity_id}


@pytest.fixture
def audit_event(db_session, tenant_context):
    result = db_session.execute(
        text("""
            INSERT INTO audit_events (
                organization_id,
                subscription_id,
                resource_type,
                resource_id,
                action_type,
                actor_type,
                actor_id,
                before_state,
                after_state
            )
            VALUES (
                :org_id,
                :sub_id,
                'clients',
                '999999',
                'UPDATE',
                'system',
                NULL,
                '{"display_name": "Old Name"}'::jsonb,
                '{"display_name": "New Name"}'::jsonb
            )
            RETURNING id
        """),
        {
            "org_id": tenant_context["org_id"],
            "sub_id": tenant_context["sub_id"],
        },
    )

    event_id = result.scalar_one()
    db_session.flush()

    return event_id


def test_delete_audit_event_is_rejected(db_session, audit_event):
    with pytest.raises(DBAPIError) as exc, db_session.begin_nested():
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


def test_update_audit_event_is_rejected(db_session, audit_event):
    with pytest.raises(DBAPIError) as exc, db_session.begin_nested():
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


def test_truncate_audit_event_is_rejected(db_session, audit_event):
    with pytest.raises(DBAPIError) as exc, db_session.begin_nested():
        db_session.execute(text("TRUNCATE TABLE audit_events"))

    assert exc.value.orig.sqlstate == "42501"


def test_application_role_has_no_update_or_delete_permissions(db_session):
    result = db_session.execute(
        text("""
            SELECT
                has_table_privilege(current_user, 'audit_events', 'UPDATE'),
                has_table_privilege(current_user, 'audit_events', 'DELETE')
        """)
    )

    can_update, can_delete = result.one()

    assert can_update is False
    assert can_delete is False


def test_client_insert_creates_audit_event(db_session, tenant_context):
    db_session.execute(
        text("""
            SELECT
                set_config('audit.user_id', '123', true),
                set_config('audit.user_type', 'membership', true)
        """)
    )

    client_id = db_session.execute(
        text("""
            INSERT INTO clients (
                organization_id,
                subscription_id,
                display_name,
                email,
                phone
            )
            VALUES (
                :org_id,
                :sub_id,
                'Audit Test Client',
                'audit-test@example.com',
                '5551234567'
            )
            RETURNING id
        """),
        {
            "org_id": tenant_context["org_id"],
            "sub_id": tenant_context["sub_id"],
        },
    ).scalar_one()

    event = (
        db_session.execute(
            text("""
                SELECT
                    organization_id,
                    subscription_id,
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
        )
        .mappings()
        .one()
    )

    assert event["organization_id"] == tenant_context["org_id"]
    assert event["subscription_id"] == tenant_context["sub_id"]
    assert event["resource_type"] == "clients"
    assert event["resource_id"] == str(client_id)
    assert event["action_type"] == "INSERT"
    assert event["actor_id"] == "123"
    assert event["actor_type"] == "membership"
    assert event["before_state"] == {}
    assert event["after_state"]["display_name"] == "Audit Test Client"


def test_client_insert_no_config_creates_system_user(db_session, tenant_context):
    client_id = db_session.execute(
        text("""
            INSERT INTO clients (
                organization_id,
                subscription_id,
                display_name,
                email,
                phone
            )
            VALUES (
                :org_id,
                :sub_id,
                'Audit Test Client',
                'audit-test@example.com',
                '5551234567'
            )
            RETURNING id
        """),
        {
            "org_id": tenant_context["org_id"],
            "sub_id": tenant_context["sub_id"],
        },
    ).scalar_one()

    event = (
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
            """),
            {"client_id": str(client_id)},
        )
        .mappings()
        .one()
    )

    assert event["resource_type"] == "clients"
    assert event["resource_id"] == str(client_id)
    assert event["action_type"] == "INSERT"
    assert event["actor_id"] is None
    assert event["actor_type"] == "system"
    assert event["before_state"] == {}
    assert event["after_state"]["display_name"] == "Audit Test Client"


def test_client_insert_wrong_user_type(db_session, tenant_context):
    db_session.execute(
        text("""
            SELECT
                set_config('audit.user_id', '123', true),
                set_config('audit.user_type', 'invalid_role', true)
        """)
    )
    with pytest.raises(IntegrityError) as exc_info, db_session.begin_nested():
        db_session.execute(
            text("""
                INSERT INTO clients (
                    organization_id,
                    subscription_id,
                    display_name,
                    email,
                    phone
                )
                VALUES (
                    :org_id,
                    :sub_id,
                    'Audit Test Client',
                    'audit-test@example.com',
                    '5551234567'
                )
                RETURNING id
            """),
            {
                "org_id": tenant_context["org_id"],
                "sub_id": tenant_context["sub_id"],
            },
        )

    assert "audit_events_actor_type_check" in str(exc_info.value)


def test_client_update_creates_accurate_audit_diff_and_skips_noop(
    db_session, tenant_context
):
    client_id = db_session.execute(
        text("""
            INSERT INTO clients (
                organization_id,
                subscription_id,
                display_name,
                email,
                phone
            )
            VALUES (
                :org_id,
                :sub_id,
                'Carrot',
                'potato@example.com',
                '1111111111'
            )
            RETURNING id
        """),
        {
            "org_id": tenant_context["org_id"],
            "sub_id": tenant_context["sub_id"],
        },
    ).scalar_one()

    db_session.execute(
        text("""
            SELECT
                set_config('audit.user_id', '123', true),
                set_config('audit.user_type', 'membership', true)
        """)
    )

    # 1. Real update -> should create 1 UPDATE audit event
    db_session.execute(
        text("""
            UPDATE clients
            SET display_name = 'Updated Name'
            WHERE id = :client_id
        """),
        {"client_id": client_id},
    )

    # 2. No-op update (same value) -> should be ignored by audit_trigger()
    db_session.execute(
        text("""
            UPDATE clients
            SET display_name = 'Updated Name'
            WHERE id = :client_id
        """),
        {"client_id": client_id},
    )

    events = (
        db_session.execute(
            text("""
                SELECT before_state, after_state
                FROM audit_events
                WHERE resource_type = 'clients'
                  AND resource_id = :client_id
                  AND action_type = 'UPDATE'
            """),
            {"client_id": str(client_id)},
        )
        .mappings()
        .all()
    )

    assert len(events) == 1
    assert events[0]["before_state"] == {"display_name": "Carrot"}
    assert events[0]["after_state"] == {"display_name": "Updated Name"}


def test_audit_event_rolls_back_with_business_transaction(db_session, tenant_context):
    nested = db_session.begin_nested()

    try:
        client_id = db_session.execute(
            text("""
                INSERT INTO clients (
                    organization_id,
                    subscription_id,
                    display_name,
                    email,
                    phone
                )
                VALUES (
                    :org_id,
                    :sub_id,
                    'Rollback Client',
                    'rollback@example.com',
                    '5553333333'
                )
                RETURNING id
            """),
            {
                "org_id": tenant_context["org_id"],
                "sub_id": tenant_context["sub_id"],
            },
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
        text("SELECT EXISTS (SELECT 1 FROM clients WHERE id = :client_id)"),
        {"client_id": client_id},
    ).scalar_one()

    audit_exists = db_session.execute(
        text("SELECT EXISTS (SELECT 1 FROM audit_events WHERE id = :event_id)"),
        {"event_id": event_id},
    ).scalar_one()

    assert client_exists is False
    assert audit_exists is False


def test_audit_events_rls_blocks_other_organizations(db_session, audit_event):
    # Switch to a different random organization UUID
    db_session.execute(
        text("SELECT set_config('app.current_org_id', gen_random_uuid()::text, true)")
    )

    visible_event = db_session.execute(
        text("SELECT id FROM audit_events WHERE id = :event_id"),
        {"event_id": audit_event},
    ).scalar_one_or_none()

    assert visible_event is None
