# import uuid
# from collections.abc import Sequence
# from typing import Any, Literal, cast, overload

# import pytest
# from psycopg import errors

# from app.core.config import settings
# from app.dependencies.db import get_admin_connection, get_connection

# TABLES = [
#     "approval_requests",
#     "agent_delegations",
#     "role_assignments",
#     "role_definitions",
#     "group_members",
#     "groups",
#     "bookings",
#     "public_prospects",
#     "availability_overrides",
#     "availability_rules",
#     "public_booking_links",
#     "tasks",
#     "meetings",
#     "meeting_types",
#     "documents",
#     "folders",
#     "notes",
#     "goals",
#     "clients",
#     "agents",
#     "subscriptions",
#     "staff_profiles",
#     "advisor_profiles",
#     "memberships",
#     "organizations",
#     "identities",
#     "feature_flags",
# ]


# def require_test_database() -> None:
#     if "test" not in settings.DB_NAME.lower():
#         pytest.fail(
#             f"Database tests must use *test* in DB_NAME (got {settings.DB_NAME!r}). "
#             "Refusing to modify another database."
#         )


# @pytest.fixture(scope="session", autouse=True)
# def schema():
#     require_test_database()
#     # Verify that the test runner is connected as the unprivileged app user (orbit_app)
#     with get_connection() as conn:
#         row = conn.execute(
#             "SELECT current_user, usesuper, usebypassrls "
#             "FROM pg_user WHERE usename = current_user"
#         ).fetchone()
#         assert row is not None
#         current_user, is_super, bypass_rls = row
#         assert current_user == settings.DB_USER
#         assert is_super is False, "App DB user must not be a superuser"
#         assert bypass_rls is False, "App DB user must have NOBYPASSRLS"
#     yield


# @pytest.fixture(autouse=True)
# def clean_tables():
#     def clean() -> None:
#         truncate_sql = (
#             f"TRUNCATE {', '.join(TABLES)}, audit_log RESTART IDENTITY CASCADE;"
#         )
#         # Privileged teardown (disabling triggers + TRUNCATE) must run as postgres
#         with get_admin_connection() as admin_conn:
#             admin_conn.execute("ALTER TABLE audit_log DISABLE TRIGGER USER;")
#             admin_conn.execute(cast(Any, truncate_sql))
#             admin_conn.execute("ALTER TABLE audit_log ENABLE TRIGGER USER;")
#             admin_conn.commit()

#     clean()
#     yield
#     clean()


# @overload
# def run(
#     sql: str,
#     params: Sequence[Any] | None = None,
#     *,
#     fetch: Literal[True],
#     org_id: Any = None,
#     bypass_rls: bool = True,
# ) -> tuple[Any, ...]: ...


# @overload
# def run(
#     sql: str,
#     params: Sequence[Any] | None = None,
#     fetch: Literal[False] = False,
#     org_id: Any = None,
#     bypass_rls: bool = True,
# ) -> None: ...


# def run(
#     sql: str,
#     params: Sequence[Any] | None = None,
#     fetch: bool = False,
#     org_id: Any = None,
#     bypass_rls: bool = True,
# ) -> tuple[Any, ...] | None:
#     """Execute one statement as orbit_app in its own transaction with RLS context."""
#     with get_connection() as conn:
#         if bypass_rls:
#             conn.execute("SET LOCAL app.bypass_rls = 'on'")
#         else:
#             conn.execute("SET LOCAL app.bypass_rls = 'off'")
#             if org_id is not None:
#                 conn.execute(
#                     "SELECT set_config('app.current_org_id', %s, true)",
#                     (str(org_id),),
#                 )
#         cur = conn.execute(cast(Any, sql), params)
#         if fetch:
#             row = cur.fetchone()
#             assert row is not None, "Expected a row when fetch=True, got None"
#             conn.commit()
#             return tuple(row)
#         conn.commit()
#         return None


# def count(
#     table: str,
#     where: str = "TRUE",
#     params: Sequence[Any] | None = None,
#     org_id: Any = None,
#     bypass_rls: bool = True,
# ) -> int:
#     row = run(
#         f"SELECT COUNT(*) FROM {table} WHERE {where}",
#         params,
#         fetch=True,
#         org_id=org_id,
#         bypass_rls=bypass_rls,
#     )
#     return int(row[0])


# # ============================================================================


# def make_identity(
#     issuer: str = "https://auth.example.com",
#     subject: str | None = None,
#     email: str = "user@example.com",
# ) -> uuid.UUID:
#     subject = subject or f"sub_{uuid.uuid4()}"
#     return run(
#         "INSERT INTO identities (issuer, subject, email) VALUES (%s, %s, %s) RETURNING id",
#         (issuer, subject, email),
#         fetch=True,
#     )[0]


# def make_org(
#     owner_identity_id: uuid.UUID | None = None,
#     name: str = "Test Org",
#     with_default_sub: bool = True,
# ) -> uuid.UUID:
#     owner_identity_id = owner_identity_id or make_identity()
#     with get_connection() as conn:
#         conn.execute("SET LOCAL app.bypass_rls = 'on'")
#         row = conn.execute(
#             "INSERT INTO organizations (name, owner_identity_id, status) "
#             "VALUES (%s, %s, %s) RETURNING id",
#             (name, owner_identity_id, "active" if with_default_sub else "provisioning"),
#         ).fetchone()
#         assert row is not None
#         org_id: uuid.UUID = row[0]

#         if with_default_sub:
#             conn.execute(
#                 "INSERT INTO subscriptions (organization_id, name, purpose, is_default, status) "
#                 "VALUES (%s, 'Default Sub', 'default', TRUE, 'active')",
#                 (org_id,),
#             )
#         conn.commit()
#         return org_id


# def make_subscription(
#     org_id: uuid.UUID | None = None,
#     name: str = "Sub",
#     purpose: str = "client_portfolio",
#     is_default: bool = False,
#     status: str = "active",
# ) -> uuid.UUID:
#     org_id = org_id or make_org()
#     return run(
#         "INSERT INTO subscriptions (organization_id, name, purpose, is_default, status) "
#         "VALUES (%s, %s, %s, %s, %s) RETURNING id",
#         (org_id, name, purpose, is_default, status),
#         fetch=True,
#     )[0]


# def make_membership(
#     org_id: uuid.UUID | None = None,
#     identity_id: uuid.UUID | None = None,
#     status: str = "active",
# ) -> uuid.UUID:
#     org_id = org_id or make_org()
#     identity_id = identity_id or make_identity()
#     return run(
#         "INSERT INTO memberships (organization_id, identity_id, status) "
#         "VALUES (%s, %s, %s) RETURNING id",
#         (org_id, identity_id, status),
#         fetch=True,
#     )[0]


# def make_tenant_context() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
#     """Creates a ready-to-use (org_id, sub_id, advisor_membership_id) tuple."""
#     identity_id = make_identity()
#     org_id = make_org(owner_identity_id=identity_id, with_default_sub=True)
#     sub_id: uuid.UUID = run(
#         "SELECT id FROM subscriptions WHERE organization_id = %s AND is_default = TRUE",
#         (org_id,),
#         fetch=True,
#     )[0]
#     membership_id = make_membership(org_id=org_id, identity_id=identity_id)
#     run(
#         "INSERT INTO advisor_profiles (organization_id, membership_id, display_name) "
#         "VALUES (%s, %s, 'Test Advisor')",
#         (org_id, membership_id),
#     )
#     return org_id, sub_id, membership_id


# def make_client(
#     org_id: uuid.UUID | None = None,
#     sub_id: uuid.UUID | None = None,
#     advisor_membership_id: uuid.UUID | None = None,
#     display_name: str = "testClient",
#     phone: str = "000-000-0000",
#     email: str = "testClient@example.com",
# ) -> uuid.UUID:
#     if org_id is None or sub_id is None:
#         org_id, sub_id, default_adv = make_tenant_context()
#         advisor_membership_id = advisor_membership_id or default_adv
#     return run(
#         "INSERT INTO clients (organization_id, subscription_id, display_name, phone, email, primary_advisor_membership_id) "
#         "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
#         (org_id, sub_id, display_name, phone, email, advisor_membership_id),
#         fetch=True,
#     )[0]


# def make_agent(
#     org_id: uuid.UUID | None = None,
#     sub_id: uuid.UUID | None = None,
#     created_by_membership_id: uuid.UUID | None = None,
#     name: str = "TestBot",
#     agent_type: str = "assistant",
# ) -> uuid.UUID:
#     if org_id is None or sub_id is None or created_by_membership_id is None:
#         org_id, sub_id, created_by_membership_id = make_tenant_context()
#     return run(
#         "INSERT INTO agents (organization_id, home_subscription_id, name, agent_type, created_by_membership_id) "
#         "VALUES (%s, %s, %s, %s, %s) RETURNING id",
#         (org_id, sub_id, name, agent_type, created_by_membership_id),
#         fetch=True,
#     )[0]


# # ============================================================================
# # Feature Flags, Identities, Organizations, Subscriptions & Profiles
# # ============================================================================


# def test_application_connection_uses_restricted_role():
#     row = run(
#         """
#         SELECT rolsuper, rolbypassrls
#         FROM pg_roles
#         WHERE rolname = current_user
#         """,
#         fetch=True,
#     )

#     assert row == (False, False)


# def test_application_role_is_not_privileged():
#     row = run(
#         """
#         SELECT
#             rolsuper,
#             rolbypassrls,
#             rolcreaterole,
#             rolcreatedb
#         FROM pg_roles
#         WHERE rolname = current_user
#         """,
#         fetch=True,
#     )

#     assert row == (False, False, False, False)


# def test_audit_log_privileges_are_append_only():
#     row = run(
#         """
#         SELECT
#             has_table_privilege(current_user, 'audit_log', 'SELECT'),
#             has_table_privilege(current_user, 'audit_log', 'INSERT'),
#             has_table_privilege(current_user, 'audit_log', 'UPDATE'),
#             has_table_privilege(current_user, 'audit_log', 'DELETE'),
#             has_table_privilege(current_user, 'audit_log', 'TRUNCATE')
#         """,
#         fetch=True,
#     )

#     assert row == (True, True, False, False, False)


# class TestFeatureFlags:
#     def test_rollout_percent_bounds(self):
#         run(
#             "INSERT INTO feature_flags (name, rollout_percent) VALUES ('valid_flag', 50)"
#         )
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO feature_flags (name, rollout_percent) VALUES ('bad_low', -1)"
#             )
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO feature_flags (name, rollout_percent) VALUES ('bad_high', 101)"
#             )


# class TestIdentitiesAndMemberships:
#     def test_issuer_subject_unique(self):
#         make_identity(issuer="https://idp.example.com", subject="user-123")
#         with pytest.raises(errors.UniqueViolation):
#             make_identity(issuer="https://idp.example.com", subject="user-123")

#     def test_soft_delete_check_constraint(self):
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO identities (issuer, subject, status, deleted_at) "
#                 "VALUES ('iss', 'sub', 'deleted', NULL)"
#             )

#     def test_membership_unique_per_org(self):
#         org_id = make_org()
#         ident_id = make_identity()
#         make_membership(org_id, ident_id)
#         with pytest.raises(errors.UniqueViolation):
#             make_membership(org_id, ident_id)

#     def test_advisor_profile_insert_and_timestamps(self):
#         org_id, _, membership_id = make_tenant_context()
#         row = run(
#             "SELECT created_at, updated_at, timezone FROM advisor_profiles "
#             "WHERE organization_id = %s AND membership_id = %s",
#             (org_id, membership_id),
#             fetch=True,
#         )
#         assert row[0] is not None and row[1] is not None
#         assert row[2] == "America/New_York"


# class TestOrganizationsAndSubscriptions:
#     def test_active_org_requires_default_subscription(self):
#         ident_id = make_identity()
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO organizations (name, owner_identity_id, status) "
#                 "VALUES ('No Default Sub Org', %s, 'active')",
#                 (ident_id,),
#             )

#     def test_only_one_active_default_subscription_per_org(self):
#         org_id = make_org(with_default_sub=True)
#         with pytest.raises(errors.UniqueViolation):
#             make_subscription(org_id=org_id, is_default=True)


# # ============================================================================
# # Clients, Goals, Notes, Folders & Documents
# # ============================================================================


# class TestClients:
#     def test_insert_valid(self):
#         assert make_client() is not None

#     def test_email_case_insensitive_unique_per_subscription(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         make_client(org_id, sub_id, adv_id, email="Client@Example.com")
#         with pytest.raises(errors.UniqueViolation):
#             make_client(org_id, sub_id, adv_id, email="client@example.com")

#     def test_display_name_not_null(self):
#         org_id, sub_id, _ = make_tenant_context()
#         with pytest.raises(errors.NotNullViolation):
#             run(
#                 "INSERT INTO clients (organization_id, subscription_id, display_name) "
#                 "VALUES (%s, %s, NULL)",
#                 (org_id, sub_id),
#             )

#     def test_onboarding_stage_invalid(self):
#         org_id, sub_id, _ = make_tenant_context()
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO clients (organization_id, subscription_id, display_name, onboarding_stage) "
#                 "VALUES (%s, %s, 'Client', 'NotAStage')",
#                 (org_id, sub_id),
#             )

#     def test_dob_range_check(self):
#         org_id, sub_id, _ = make_tenant_context()
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO clients (organization_id, subscription_id, display_name, date_of_birth) "
#                 "VALUES (%s, %s, 'Client', '1850-01-01')",
#                 (org_id, sub_id),
#             )

#     def test_fk_invalid_advisor_membership(self):
#         org_id, sub_id, _ = make_tenant_context()
#         with pytest.raises(errors.ForeignKeyViolation):
#             make_client(org_id, sub_id, advisor_membership_id=uuid.uuid4())


# class TestGoals:
#     @pytest.mark.parametrize("duration", ["short_term", "medium_term", "long_term"])
#     def test_duration_valid(self, duration):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         run(
#             "INSERT INTO goals (organization_id, subscription_id, client_id, name, duration) "
#             "VALUES (%s, %s, %s, 'Retirement', %s)",
#             (org_id, sub_id, cid, duration),
#         )

#     def test_duration_invalid(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO goals (organization_id, subscription_id, client_id, name, duration) "
#                 "VALUES (%s, %s, %s, 'Retirement', 'NotADuration')",
#                 (org_id, sub_id, cid),
#             )

#     def test_cross_subscription_client_fk_rejected(self):
#         org_id, sub_id_1, adv_id = make_tenant_context()
#         sub_id_2 = make_subscription(org_id=org_id, name="Second Sub")
#         cid = make_client(org_id, sub_id_1, adv_id)
#         with pytest.raises(errors.ForeignKeyViolation):
#             run(
#                 "INSERT INTO goals (organization_id, subscription_id, client_id, name) "
#                 "VALUES (%s, %s, %s, 'Cross-Sub Goal')",
#                 (org_id, sub_id_2, cid),
#             )


# class TestNotes:
#     def test_insert_valid_with_membership_or_agent_author(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         ag_id = make_agent(org_id, sub_id, adv_id)

#         run(
#             "INSERT INTO notes (organization_id, subscription_id, client_id, title, content, author_membership_id) "
#             "VALUES (%s, %s, %s, 'Advisor Note', 'Content', %s)",
#             (org_id, sub_id, cid, adv_id),
#         )
#         run(
#             "INSERT INTO notes (organization_id, subscription_id, client_id, title, content, author_agent_id) "
#             "VALUES (%s, %s, %s, 'Agent Note', 'Content', %s)",
#             (org_id, sub_id, cid, ag_id),
#         )
#         assert count("notes") == 2

#     def test_single_author_check_rejects_both_or_neither(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         ag_id = make_agent(org_id, sub_id, adv_id)

#         # Neither author set
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO notes (organization_id, subscription_id, client_id, title, content) "
#                 "VALUES (%s, %s, %s, 'No Author', 'Content')",
#                 (org_id, sub_id, cid),
#             )

#         # Both authors set
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO notes (organization_id, subscription_id, client_id, title, content, author_membership_id, author_agent_id) "
#                 "VALUES (%s, %s, %s, 'Both Authors', 'Content', %s, %s)",
#                 (org_id, sub_id, cid, adv_id, ag_id),
#             )

#     def test_cross_tenant_author_rejected_by_composite_fk(self):
#         org_1, sub_1, adv_1 = make_tenant_context()
#         _, _, adv_2 = make_tenant_context()
#         cid_1 = make_client(org_1, sub_1, adv_1)

#         with pytest.raises(errors.ForeignKeyViolation):
#             run(
#                 "INSERT INTO notes (organization_id, subscription_id, client_id, title, content, author_membership_id) "
#                 "VALUES (%s, %s, %s, 'Cross Tenant', 'Content', %s)",
#                 (org_1, sub_1, cid_1, adv_2),
#             )


# class TestFoldersAndDocuments:
#     def test_folder_cycle_detection_trigger(self):
#         org_id, sub_id, _ = make_tenant_context()
#         f_root = run(
#             "INSERT INTO folders (organization_id, subscription_id, name, status) "
#             "VALUES (%s, %s, 'Root', 'active') RETURNING id",
#             (org_id, sub_id),
#             fetch=True,
#         )[0]
#         f_child = run(
#             "INSERT INTO folders (organization_id, subscription_id, parent_folder_id, name, status) "
#             "VALUES (%s, %s, %s, 'Child', 'active') RETURNING id",
#             (org_id, sub_id, f_root),
#             fetch=True,
#         )[0]

#         # Moving f_root inside f_child must trigger cycle detection
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "UPDATE folders SET parent_folder_id = %s WHERE id = %s",
#                 (f_child, f_root),
#             )

#     def test_document_defaults_and_workflow_status(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         row = run(
#             "INSERT INTO documents (organization_id, subscription_id, client_id, name) "
#             "VALUES (%s, %s, %s, 'Tax Return.pdf') RETURNING workflow_status, classification",
#             (org_id, sub_id, cid),
#             fetch=True,
#         )
#         assert row[0] == "unsent"
#         assert row[1] == "confidential"

#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO documents (organization_id, subscription_id, client_id, name, workflow_status) "
#                 "VALUES (%s, %s, %s, 'Bad.pdf', 'InvalidWorkflowStatus')",
#                 (org_id, sub_id, cid),
#             )


# # ============================================================================
# # Meetings, Bookings & Tasks
# # ============================================================================


# class TestMeetingsAndBookings:
#     def test_meeting_insert_and_generated_columns(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         row = run(
#             "INSERT INTO meetings ("
#             "  organization_id, subscription_id, advisor_membership_id, client_id, "
#             "  title, organizer_membership_id, scheduled_range, status"
#             ") VALUES ("
#             "  %s, %s, %s, %s, 'Intro Call', %s, "
#             "  tstzrange('2026-11-01 14:00:00+00', '2026-11-01 14:45:00+00', '[)'), 'active'"
#             ") RETURNING duration_minutes, completion_status",
#             (org_id, sub_id, adv_id, cid, adv_id),
#             fetch=True,
#         )
#         assert row[0] == 45
#         assert row[1] == "scheduled"

#     def test_advisor_busy_meeting_overlap_exclusion(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         run(
#             "INSERT INTO meetings ("
#             "  organization_id, subscription_id, advisor_membership_id, title, "
#             "  organizer_membership_id, scheduled_range, status, is_busy"
#             ") VALUES ("
#             "  %s, %s, %s, 'Meeting 1', %s, "
#             "  tstzrange('2026-11-01 10:00:00+00', '2026-11-01 11:00:00+00', '[)'), 'active', TRUE"
#             ")",
#             (org_id, sub_id, adv_id, adv_id),
#         )
#         # Overlapping active busy meeting for the same advisor must fail with ExclusionViolation
#         with pytest.raises(errors.ExclusionViolation):
#             run(
#                 "INSERT INTO meetings ("
#                 "  organization_id, subscription_id, advisor_membership_id, title, "
#                 "  organizer_membership_id, scheduled_range, status, is_busy"
#                 ") VALUES ("
#                 "  %s, %s, %s, 'Overlapping Meeting', %s, "
#                 "  tstzrange('2026-11-01 10:30:00+00', '2026-11-01 11:30:00+00', '[)'), 'active', TRUE"
#                 ")",
#                 (org_id, sub_id, adv_id, adv_id),
#             )

#     def test_booking_conflicts_with_busy_internal_meeting(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         mt_id = run(
#             "INSERT INTO meeting_types (organization_id, subscription_id, advisor_membership_id, slug, title) "
#             "VALUES (%s, %s, %s, 'intro-30', 'Intro 30m') RETURNING id",
#             (org_id, sub_id, adv_id),
#             fetch=True,
#         )[0]
#         link_id = run(
#             "INSERT INTO public_booking_links ("
#             "  organization_id, subscription_id, organizer_membership_id, advisor_membership_id, "
#             "  meeting_type_id, public_token, title, expires_at"
#             ") VALUES (%s, %s, %s, %s, %s, 'tok_123', 'Book Me', NOW() + INTERVAL '7 days') RETURNING id",
#             (org_id, sub_id, adv_id, adv_id, mt_id),
#             fetch=True,
#         )[0]

#         # Insert an active busy internal meeting at 15:00-16:00
#         run(
#             "INSERT INTO meetings ("
#             "  organization_id, subscription_id, advisor_membership_id, title, "
#             "  organizer_membership_id, scheduled_range, status, is_busy"
#             ") VALUES ("
#             "  %s, %s, %s, 'Internal Block', %s, "
#             "  tstzrange('2026-11-02 15:00:00+00', '2026-11-02 16:00:00+00', '[)'), 'active', TRUE"
#             ")",
#             (org_id, sub_id, adv_id, adv_id),
#         )

#         # Attempting to hold a booking during 15:30-16:00 must fail via trigger
#         with pytest.raises(errors.ExclusionViolation):
#             run(
#                 "INSERT INTO bookings ("
#                 "  organization_id, subscription_id, advisor_membership_id, booking_link_id, "
#                 "  meeting_type_id, status, slot_range, reserved_range, hold_expires_at, idempotency_key"
#                 ") VALUES ("
#                 "  %s, %s, %s, %s, %s, 'HELD', "
#                 "  tstzrange('2026-11-02 15:30:00+00', '2026-11-02 16:00:00+00', '[)'), "
#                 "  tstzrange('2026-11-02 15:30:00+00', '2026-11-02 16:00:00+00', '[)'), "
#                 "  NOW() + INTERVAL '10 minutes', 'idem_1'"
#                 ")",
#                 (org_id, sub_id, adv_id, link_id, mt_id),
#             )


# class TestTasks:
#     def test_default_task_status_and_completed_at_invariant(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)
#         ag_id = make_agent(org_id, sub_id, adv_id)

#         row = run(
#             "INSERT INTO tasks (organization_id, subscription_id, client_id, title, assignee_agent_id, assigned_at) "
#             "VALUES (%s, %s, %s, 'Draft Plan', %s, NOW()) RETURNING task_status",
#             (org_id, sub_id, cid, ag_id),
#             fetch=True,
#         )
#         assert row[0] == "todo"

#         # Marking task_status = 'completed' without completed_at must fail
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO tasks (organization_id, subscription_id, client_id, title, task_status, completed_at) "
#                 "VALUES (%s, %s, %s, 'Done Task', 'completed', NULL)",
#                 (org_id, sub_id, cid),
#             )

#     def test_single_assignee_check_rejects_both_membership_and_agent(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         ag_id = make_agent(org_id, sub_id, adv_id)
#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO tasks ("
#                 "  organization_id, subscription_id, title, assignee_membership_id, assignee_agent_id"
#                 ") VALUES (%s, %s, 'Dual Assignee', %s, %s)",
#                 (org_id, sub_id, adv_id, ag_id),
#             )


# # ============================================================================
# # RBAC, Agent Delegations, Approvals, Audit Log & Row-Level Security
# # ============================================================================


# class TestRBACAndGovernance:
#     def test_role_assignment_scope_matches_role_definition(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)

#         goal_role_id = run(
#             "INSERT INTO role_definitions (organization_id, name, resource_scope_type, capabilities) "
#             "VALUES (%s, 'goal_editor', 'goal', ARRAY['view', 'edit']) RETURNING id",
#             (org_id,),
#             fetch=True,
#         )[0]
#         goal_id = run(
#             "INSERT INTO goals (organization_id, subscription_id, client_id, name) "
#             "VALUES (%s, %s, %s, 'Save for house') RETURNING id",
#             (org_id, sub_id, cid),
#             fetch=True,
#         )[0]

#         # Valid goal role assignment
#         run(
#             "INSERT INTO role_assignments ("
#             "  organization_id, subscription_id, role_definition_id, "
#             "  subject_membership_id, scope_type, scope_id, granted_by_membership_id, status"
#             ") VALUES (%s, %s, %s, %s, 'goal', %s, %s, 'active')",
#             (org_id, sub_id, goal_role_id, adv_id, goal_id, adv_id),
#         )

#         # Assigning a 'goal' role_definition to a 'client' scope_type must fail FK check
#         with pytest.raises(errors.ForeignKeyViolation):
#             run(
#                 "INSERT INTO role_assignments ("
#                 "  organization_id, subscription_id, role_definition_id, "
#                 "  subject_membership_id, scope_type, scope_id, granted_by_membership_id, status"
#                 ") VALUES (%s, %s, %s, %s, 'client', %s, %s, 'active')",
#                 (org_id, sub_id, goal_role_id, adv_id, cid, adv_id),
#             )

#     def test_agent_delegation_restricts_capabilities_to_view_and_propose(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         ag_id = make_agent(org_id, sub_id, adv_id)

#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO agent_delegations ("
#                 "  organization_id, agent_id, target_subscription_id, capabilities, "
#                 "  granted_by_membership_id, expires_at"
#                 ") VALUES (%s, %s, %s, ARRAY['view', 'delete'], %s, NOW() + INTERVAL '1 hour')",
#                 (org_id, ag_id, sub_id, adv_id),
#             )

#     def test_approval_request_prevents_self_approval(self):
#         org_id, sub_id, adv_id = make_tenant_context()
#         cid = make_client(org_id, sub_id, adv_id)

#         with pytest.raises(errors.CheckViolation):
#             run(
#                 "INSERT INTO approval_requests ("
#                 "  organization_id, subscription_id, requesting_membership_id, approver_membership_id, "
#                 "  action_type, target_resource_type, target_resource_id, action_payload, "
#                 "  normalized_action_payload_hash, idempotency_key, expires_at, status, approved_at"
#                 ") VALUES ("
#                 "  %s, %s, %s, %s, 'delete_client', 'client', %s, '{}'::jsonb, "
#                 "  'hash123', 'idem_self', NOW() + INTERVAL '1 hour', 'approved', NOW()"
#                 ")",
#                 (org_id, sub_id, adv_id, adv_id, cid),
#             )


# class TestAuditLogAndRLS:
#     def test_audit_log_is_append_only(self):
#         org_id, _, _ = make_tenant_context()
#         log_id = run(
#             "INSERT INTO audit_log ("
#             "  organization_id, actor_type, actor_id, effective_subject_id, "
#             "  action, target_type, target_id, authorization_decision, outcome, reason_code"
#             ") VALUES (%s, 'user', 'm1', 'm1', 'client.view', 'client', 'c1', 'allow', 'success', 'OK') "
#             "RETURNING id",
#             (org_id,),
#             fetch=True,
#         )[0]

#         with pytest.raises(errors.InsufficientPrivilege):
#             run("UPDATE audit_log SET outcome = 'denied' WHERE id = %s", (log_id,))

#         with pytest.raises(errors.InsufficientPrivilege):
#             run("DELETE FROM audit_log WHERE id = %s", (log_id,))

#     def test_rls_isolates_tenants(self):
#         org_1, sub_1, adv_1 = make_tenant_context()
#         org_2, sub_2, adv_2 = make_tenant_context()
#         make_client(org_1, sub_1, adv_1, email="org1@example.com")
#         make_client(org_2, sub_2, adv_2, email="org2@example.com")

#         # Scoped to org_1: sees only 1 client
#         assert count("clients", org_id=org_1, bypass_rls=False) == 1
#         # Scoped to org_2: sees only 1 client
#         assert count("clients", org_id=org_2, bypass_rls=False) == 1
#         # With no org_id set and bypass_rls=False: sees 0 clients
#         assert count("clients", org_id=None, bypass_rls=False) == 0
