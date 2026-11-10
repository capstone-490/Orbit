# 50% or more AI-generated code
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid7

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import TSTZRANGE, Range
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities import Booking
from app.domain.enums import BookingStatus, MeetingMode
from app.domain.exceptions import SlotOverlapConflictError
from app.domain.structs import TimeWindow
from app.infrastructure.repositories.helpers import _is_exclusion_violation
from app.infrastructure.uow import SqlAlchemyUnitOfWork


@pytest.fixture
async def seeded_tenant(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, object]:
    """
    Seeds a clean Organization, default Subscription, Advisor Membership + Profile,
    MeetingType (30m with 5m before / 10m after buffers), and PublicBookingLink.
    """
    org_id = uuid7()
    sub_id = uuid7()
    identity_id = uuid7()
    membership_id = uuid7()
    mt_id = uuid7()
    link_id = uuid7()
    now = datetime.now(tz=UTC)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id, bypass_rls=True)
        assert uow._session is not None
        session = uow._session

        await session.execute(
            text(
                "INSERT INTO identities (id, issuer, subject, email, status) "
                "VALUES (:id, 'https://auth.example.com', :sub, 'advisor@example.com', 'active')"
            ),
            {"id": identity_id, "sub": f"sub_{identity_id}"},
        )
        await session.execute(
            text(
                "INSERT INTO organizations (id, name, owner_identity_id, status) "
                "VALUES (:id, 'Acme Wealth', :owner_id, 'active')"
            ),
            {"id": org_id, "owner_id": identity_id},
        )
        await session.execute(
            text(
                "INSERT INTO subscriptions (id, organization_id, name, purpose, is_default, status) "
                "VALUES (:id, :org_id, 'Default Portfolio', 'default', TRUE, 'active')"
            ),
            {"id": sub_id, "org_id": org_id},
        )
        await session.execute(
            text(
                "INSERT INTO memberships (id, organization_id, identity_id, status) "
                "VALUES (:id, :org_id, :identity_id, 'active')"
            ),
            {"id": membership_id, "org_id": org_id, "identity_id": identity_id},
        )
        await session.execute(
            text(
                "INSERT INTO advisor_profiles (organization_id, membership_id, display_name, timezone, booking_enabled) "
                "VALUES (:org_id, :mem_id, 'Jane Doe, CFA', 'America/New_York', TRUE)"
            ),
            {"org_id": org_id, "mem_id": membership_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO meeting_types (
                    id, organization_id, subscription_id, advisor_membership_id,
                    slug, title, duration_minutes, slot_interval_minutes,
                    buffer_before_minutes, buffer_after_minutes,
                    minimum_notice_minutes, max_days_in_advance, meeting_mode, is_active
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    'intro-30', '30-Min Intro Call', 30, 15,
                    5, 10, 60, 60, 'video', TRUE
                )
                """
            ),
            {
                "id": mt_id,
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": membership_id,
            },
        )

        public_token = f"tok_{uuid7().hex}"
        await session.execute(
            text(
                """
                INSERT INTO public_booking_links (
                    id, organization_id, subscription_id, organizer_membership_id,
                    advisor_membership_id, meeting_type_id, public_token,
                    title, is_active, hold_ttl_seconds, expires_at
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    :adv_id, :mt_id, :token,
                    'Book with Jane', TRUE, 300, :expires_at
                )
                """
            ),
            {
                "id": link_id,
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": membership_id,
                "mt_id": mt_id,
                "token": public_token,
                "expires_at": now + timedelta(days=30),
            },
        )
        await uow.commit()

    return {
        "org_id": org_id,
        "sub_id": sub_id,
        "advisor_id": membership_id,
        "mt_id": mt_id,
        "link_id": link_id,
        "public_token": public_token,
        "now": now,
    }


# =============================================================================
# Booking Link Resolution (Valid, Expired, Unknown)
# =============================================================================
async def test_get_active_booking_link_valid_expired_and_unknown_tokens(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)

        # 1. Valid active token resolves link, meeting_type, and advisor display name
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, advisor_name = resolved
        assert link.public_token == public_token
        assert meeting_type.slug == "intro-30"
        assert meeting_type.duration_minutes == 30
        assert meeting_type.buffers.before_minutes == 5
        assert meeting_type.buffers.after_minutes == 10
        assert meeting_type.meeting_mode == MeetingMode.VIDEO
        assert advisor_name == "Jane Doe, CFA"

        # 2. Unknown token returns None
        unknown = await uow.schedules.get_active_booking_link("tok_nonexistent", now)
        assert unknown is None

        # 3. Querying after link expiration timestamp returns None
        expired = await uow.schedules.get_active_booking_link(
            public_token, now + timedelta(days=31)
        )
        assert expired is None


# =============================================================================
# Advisor Recurring Availability Rules
# =============================================================================
async def test_get_advisor_rules_returns_only_active_ordered_by_day_and_time(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        session = uow._session

        # Insert Wednesday afternoon, Monday morning, and an inactive Tuesday rule
        await session.execute(
            text(
                """
                INSERT INTO availability_rules (
                    id, organization_id, advisor_membership_id, day_of_week,
                    start_time, end_time, timezone, is_active, valid_from
                ) VALUES
                (:id1, :org_id, :adv_id, 3, '13:00', '17:00', 'America/New_York', TRUE, CURRENT_DATE),
                (:id2, :org_id, :adv_id, 1, '09:00', '12:00', 'America/New_York', TRUE, CURRENT_DATE),
                (:id3, :org_id, :adv_id, 2, '09:00', '17:00', 'America/New_York', FALSE, CURRENT_DATE)
                """
            ),
            {
                "id1": uuid7(),
                "id2": uuid7(),
                "id3": uuid7(),
                "org_id": org_id,
                "adv_id": advisor_id,
            },
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        rules = await uow.schedules.get_advisor_rules(org_id, advisor_id)

        assert len(rules) == 2
        assert [r.day_of_week for r in rules] == [1, 3]
        assert rules[0].start_time == time(9, 0)
        assert rules[0].end_time == time(12, 0)
        assert rules[1].start_time == time(13, 0)
        assert rules[1].end_time == time(17, 0)


# =============================================================================
# Advisor Date Overrides (Closures & Custom Hours)
# =============================================================================
async def test_get_advisor_overrides_filters_by_date_and_maps_custom_windows(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]

    day_closed = (now + timedelta(days=7)).date()
    day_custom = (now + timedelta(days=8)).date()
    day_outside = (now + timedelta(days=20)).date()

    custom_start = datetime.combine(day_custom, time(10, 0), tzinfo=UTC)
    custom_end = datetime.combine(day_custom, time(14, 0), tzinfo=UTC)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        session = uow._session

        # 1. Full-day holiday closure (is_available = FALSE, custom_window = NULL)
        await session.execute(
            text(
                """
                INSERT INTO availability_overrides (
                    id, organization_id, advisor_membership_id,
                    override_date, is_available, custom_window, reason
                ) VALUES (
                    :id, :org_id, :adv_id,
                    :override_date, FALSE, NULL, 'Company Holiday'
                )
                """
            ),
            {
                "id": uuid7(),
                "org_id": org_id,
                "adv_id": advisor_id,
                "override_date": day_closed,
            },
        )

        # 2. Custom open window (is_available = TRUE, custom_window = [10:00, 14:00))
        await session.execute(
            text(
                """
                INSERT INTO availability_overrides (
                    id, organization_id, advisor_membership_id,
                    override_date, is_available, custom_window, reason
                ) VALUES (
                    :id, :org_id, :adv_id,
                    :override_date, TRUE, :custom_window, 'Special Saturday Hours'
                )
                """
            ).bindparams(bindparam("custom_window", type_=TSTZRANGE)),
            {
                "id": uuid7(),
                "org_id": org_id,
                "adv_id": advisor_id,
                "override_date": day_custom,
                "custom_window": Range(custom_start, custom_end, bounds="[)"),
            },
        )

        # 3. Override outside the queried range
        await session.execute(
            text(
                """
                INSERT INTO availability_overrides (
                    id, organization_id, advisor_membership_id,
                    override_date, is_available, custom_window, reason
                ) VALUES (
                    :id, :org_id, :adv_id,
                    :override_date, FALSE, NULL, 'Future Conference'
                )
                """
            ),
            {
                "id": uuid7(),
                "org_id": org_id,
                "adv_id": advisor_id,
                "override_date": day_outside,
            },
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        overrides = await uow.schedules.get_advisor_overrides(
            org_id,
            advisor_id,
            start_date=day_closed,
            end_date=day_custom,
        )
        by_date = {ov.override_date: ov for ov in overrides}
        assert len(by_date) == 2

        closed_ov = by_date[day_closed]
        assert closed_ov.is_available is False
        assert closed_ov.custom_window is None
        assert closed_ov.reason == "Company Holiday"

        custom_ov = by_date[day_custom]
        assert custom_ov.is_available is True
        assert custom_ov.custom_window == TimeWindow(custom_start, custom_end)
        assert custom_ov.reason == "Special Saturday Hours"


# =============================================================================
# Idempotency Key Lookup & Duplicate Prevention
# =============================================================================
async def test_get_by_idempotency_key_and_unique_constraint(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    idem_key = f"idem-unique-{uuid7()}"

    slot_1_start = (now + timedelta(days=2)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    slot_2_start = slot_1_start + timedelta(hours=2)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=TimeWindow(slot_1_start, slot_1_start + timedelta(minutes=30)),
            prospect_timezone="UTC",
            idempotency_key=idem_key,
            now=now,
        )
        await uow.bookings.add(hold)
        await uow.commit()

    # Lookup by idempotency_key returns the persisted booking
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        found = await uow.bookings.get_by_idempotency_key(org_id, idem_key)
        assert found is not None
        assert found.id == hold.id
        assert found.idempotency_key == idem_key

        missing = await uow.bookings.get_by_idempotency_key(
            org_id, "idem-does-not-exist"
        )
        assert missing is None

    # Attempting to insert a second booking with the same (organization_id, idempotency_key)
    # even at a non-overlapping time fails with IntegrityError
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        duplicate_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=TimeWindow(slot_2_start, slot_2_start + timedelta(minutes=30)),
            prospect_timezone="UTC",
            idempotency_key=idem_key,
            now=now,
        )
        with pytest.raises(IntegrityError):
            await uow.bookings.add(duplicate_hold)


# =============================================================================
# Prospect Upsert & Client Deduplication
# =============================================================================
async def test_upsert_prospect_and_provision_client_is_idempotent_case_insensitive(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)

        (
            prospect_id_1,
            client_id_1,
        ) = await uow.bookings.upsert_prospect_and_provision_client(
            organization_id=org_id,
            subscription_id=sub_id,
            advisor_membership_id=advisor_id,
            email="  Sam.Investor@Example.com ",
            full_name="Sam Investor",
            phone=None,
            company_name=None,
        )

        # Second call with lowercase email and enriched phone/company updates in-place
        (
            prospect_id_2,
            client_id_2,
        ) = await uow.bookings.upsert_prospect_and_provision_client(
            organization_id=org_id,
            subscription_id=sub_id,
            advisor_membership_id=advisor_id,
            email="sam.investor@example.com",
            full_name="Sam Investor Jr.",
            phone="+15145550100",
            company_name="Investor Corp",
        )
        await uow.commit()

    assert prospect_id_1 == prospect_id_2
    assert client_id_1 == client_id_2

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        row = (
            (
                await uow._session.execute(
                    text(
                        "SELECT full_name, phone, company_name, linked_client_id "
                        "FROM public_prospects WHERE id = :id"
                    ),
                    {"id": prospect_id_1},
                )
            )
            .mappings()
            .one()
        )
        assert row["full_name"] == "Sam Investor Jr."
        assert row["phone"] == "+15145550100"
        assert row["company_name"] == "Investor Corp"
        assert row["linked_client_id"] == client_id_1


# =============================================================================
# Opaque Busy Windows Privacy Wall & Exclusions
# =============================================================================
async def test_get_opaque_busy_windows_filters_active_and_respects_exclusions(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    day_base = (now + timedelta(days=7)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    active_hold_slot = TimeWindow(day_base, day_base + timedelta(minutes=30))
    expired_hold_slot = TimeWindow(
        day_base + timedelta(hours=2),
        day_base + timedelta(hours=2, minutes=30),
    )
    busy_meeting_slot = TimeWindow(
        day_base + timedelta(hours=4),
        day_base + timedelta(hours=4, minutes=30),
    )
    free_meeting_slot = TimeWindow(
        day_base + timedelta(hours=6),
        day_base + timedelta(hours=6, minutes=30),
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        session = uow._session

        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        # 1. Active hold -> included
        active_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=active_hold_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(active_hold)

        # 2. Expired hold -> excluded
        expired_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=expired_hold_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        expired_hold.hold_expires_at = now - timedelta(minutes=5)
        await uow.bookings.add(expired_hold)

        # 3. Active busy internal meeting -> included
        await session.execute(
            text(
                """
                INSERT INTO meetings (
                    id, organization_id, subscription_id, advisor_membership_id,
                    title, meeting_mode, is_busy, organizer_membership_id,
                    scheduled_range, status
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    'Busy Internal Call', 'video', TRUE, :adv_id,
                    :scheduled_range, 'active'
                )
                """
            ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE)),
            {
                "id": uuid7(),
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": advisor_id,
                "scheduled_range": Range(
                    busy_meeting_slot.start_at,
                    busy_meeting_slot.end_at,
                    bounds="[)",
                ),
            },
        )

        # 4. Non-busy internal reminder (is_busy = FALSE) -> excluded
        await session.execute(
            text(
                """
                INSERT INTO meetings (
                    id, organization_id, subscription_id, advisor_membership_id,
                    title, meeting_mode, is_busy, organizer_membership_id,
                    scheduled_range, status
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    'FYI Reminder', 'video', FALSE, :adv_id,
                    :scheduled_range, 'active'
                )
                """
            ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE)),
            {
                "id": uuid7(),
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": advisor_id,
                "scheduled_range": Range(
                    free_meeting_slot.start_at,
                    free_meeting_slot.end_at,
                    bounds="[)",
                ),
            },
        )
        await uow.commit()

    search_window = TimeWindow(
        day_base - timedelta(hours=1),
        day_base + timedelta(hours=8),
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)

        busy_windows = await uow.schedules.get_opaque_busy_windows(
            organization_id=org_id,
            advisor_membership_id=advisor_id,
            search_window=search_window,
            now=now,
        )
        assert len(busy_windows) == 2
        assert active_hold.reserved_window in busy_windows
        assert busy_meeting_slot in busy_windows

        # Excluding `active_hold.id` omits that booking from busy windows
        busy_excluding_hold = await uow.schedules.get_opaque_busy_windows(
            organization_id=org_id,
            advisor_membership_id=advisor_id,
            search_window=search_window,
            now=now,
            exclude_booking_id=active_hold.id,
        )
        assert busy_excluding_hold == [busy_meeting_slot]


# =============================================================================
# Hold -> Confirm -> Provision Client, Meeting, Task
# =============================================================================
async def test_hold_and_confirm_booking_persists_all_aggregates(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    cancel_token_hash = f"hash_{uuid7().hex}"

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, advisor_name = resolved
        assert advisor_name == "Jane Doe, CFA"

        start = (now + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
        slot = TimeWindow(start, start + timedelta(minutes=30))

        # 1. Acquire soft hold
        booking = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=slot,
            prospect_timezone="America/New_York",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(booking)

        # 2. Upsert prospect & provision client
        (
            prospect_id,
            client_id,
        ) = await uow.bookings.upsert_prospect_and_provision_client(
            organization_id=link.organization_id,
            subscription_id=link.subscription_id,
            advisor_membership_id=meeting_type.advisor_membership_id,
            email="Alex.Prospect@Example.com",
            full_name="Alex Prospect",
            phone="+15145550199",
            company_name="Prospect Holdings",
        )

        # 3. Confirm domain booking first so topic/notes/client_id are populated
        # and hold expiration is validated prior to provisioning meetings/tasks
        booking.confirm(
            prospect_id=prospect_id,
            client_id=client_id,
            cancel_token_hash=cancel_token_hash,
            meeting_topic="Retirement Rollover",
            prospect_notes="401k consolidation",
            now=now + timedelta(seconds=30),
        )

        # 4. Create internal meeting
        internal_meeting_id = await uow.bookings.create_internal_meeting(
            booking=booking,
            meeting_type=meeting_type,
            prospect_full_name="Alex Prospect",
            prospect_email="alex.prospect@example.com",
        )

        # 5. Persist confirmed booking state
        await uow.bookings.save(booking)
        await uow.commit()

    # Verify all persisted aggregates in a fresh Unit of Work transaction
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        session = uow._session

        saved = await uow.bookings.get_by_id(org_id, link.subscription_id, booking.id)
        assert saved is not None
        assert saved.status == BookingStatus.CONFIRMED
        assert saved.internal_meeting_id == internal_meeting_id
        assert saved.prospect_id == prospect_id
        assert saved.client_id == client_id
        assert saved.meeting_topic == "Retirement Rollover"
        assert saved.prospect_notes == "401k consolidation"
        assert saved.hold_expires_at is None
        assert saved.version == 2

        by_token = await uow.bookings.get_by_cancel_token_hash(cancel_token_hash)
        assert by_token is not None
        assert by_token.id == booking.id

        prospect_row = (
            (
                await session.execute(
                    text(
                        "SELECT email, linked_client_id FROM public_prospects WHERE id = :id"
                    ),
                    {"id": prospect_id},
                )
            )
            .mappings()
            .one()
        )
        assert prospect_row["email"] == "alex.prospect@example.com"
        assert prospect_row["linked_client_id"] == client_id

        meeting_row = (
            (
                await session.execute(
                    text(
                        "SELECT status, agenda, duration_minutes, scheduled_at "
                        "FROM meetings WHERE id = :id"
                    ),
                    {"id": internal_meeting_id},
                )
            )
            .mappings()
            .one()
        )
        assert meeting_row["status"] == "active"
        assert meeting_row["agenda"] == "Retirement Rollover"
        assert meeting_row["duration_minutes"] == 30
        assert meeting_row["scheduled_at"] == slot.start_at


# =============================================================================
# CONCURRENCY FAILURE CASE: GiST Exclusion Rejects Overlapping Buffer Window
# =============================================================================
async def test_gist_exclusion_rejects_overlapping_booking_including_buffers(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    Booking 1 is 14:00 - 14:30 (with 5m before / 10m after buffer -> reserved 13:55 - 14:40).
    Booking 2 tries to book 14:30 - 15:00 (reserved 14:25 - 15:10).
    Even though the raw slots [14:00, 14:30) and [14:30, 15:00) only touch at 14:30,
    their `reserved_range` windows overlap. PostgreSQL GiST must raise SlotOverlapConflictError.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    base_start = (now + timedelta(days=3)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        hold_1 = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=TimeWindow(base_start, base_start + timedelta(minutes=30)),
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(hold_1)
        await uow.commit()

    # Attempt overlapping hold_2 starting immediately at base_start + 30m (violates 10m after-buffer)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        hold_2 = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=TimeWindow(
                base_start + timedelta(minutes=30),
                base_start + timedelta(minutes=60),
            ),
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        with pytest.raises(SlotOverlapConflictError):
            await uow.bookings.add(hold_2)


# =============================================================================
# EDGE CASE: Trigger Automatically Evicts Stale Expired Hold on New Insert
# =============================================================================
async def test_jit_trigger_evicts_expired_hold_allowing_new_booking_to_succeed(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    If Hold 1 is still marked status='HELD' in the database, but its `hold_expires_at`
    is in the past (`<= now()`), inserting Hold 2 for the exact same slot automatically
    flips Hold 1 to 'EXPIRED' inside the BEFORE INSERT trigger and succeeds.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    slot_start = (now + timedelta(days=4)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )
    slot = TimeWindow(slot_start, slot_start + timedelta(minutes=30))

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        stale_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        # Backdate hold_expires_at to 1 minute in the past so it is already expired in DB
        stale_hold.hold_expires_at = datetime.now(tz=UTC) - timedelta(minutes=1)
        await uow.bookings.add(stale_hold)
        await uow.commit()

    # Prospect 2 reserves the exact same slot in a new transaction
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        fresh_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(fresh_hold)
        await uow.commit()

    # Verify in a separate transaction (since `SET LOCAL app.current_org_id` resets on COMMIT)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        evicted = await uow.bookings.get_by_id(
            org_id, link.subscription_id, stale_hold.id
        )
        assert evicted is not None
        assert evicted.status == BookingStatus.EXPIRED
        assert evicted.version == stale_hold.version + 1
        assert evicted.hold_expires_at is not None

        active_hold = await uow.bookings.get_by_id(
            org_id, link.subscription_id, fresh_hold.id
        )
        assert active_hold is not None
        assert active_hold.status == BookingStatus.HELD


# =============================================================================
# CROSS-TABLE TRIGGER CASE: Internal Advisor Meeting Blocks Public Hold
# =============================================================================
async def test_internal_busy_meeting_blocks_overlapping_public_hold(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    If an advisor has a private internal meeting in `meetings` at 16:00 - 16:30,
    `trg_bookings_jit_evict_and_check_meetings` rejects a public booking for that window with 23P01.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]
    busy_start = (now + timedelta(days=5)).replace(
        hour=16, minute=0, second=0, microsecond=0
    )
    busy_slot = TimeWindow(busy_start, busy_start + timedelta(minutes=30))

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        await uow._session.execute(
            text(
                """
                INSERT INTO meetings (
                    id, organization_id, subscription_id, advisor_membership_id,
                    title, meeting_mode, is_busy, organizer_membership_id,
                    scheduled_range, status
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    'Confidential Portfolio Audit', 'video', TRUE, :adv_id,
                    :scheduled_range, 'active'
                )
                """
            ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE)),
            {
                "id": uuid7(),
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": advisor_id,
                "scheduled_range": Range(
                    busy_slot.start_at, busy_slot.end_at, bounds="[)"
                ),
            },
        )
        await uow.commit()

    # Attempt to create a public hold overlapping 16:00 - 16:30
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        conflicting_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=busy_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        with pytest.raises(SlotOverlapConflictError):
            await uow.bookings.add(conflicting_hold)


# =============================================================================
# CROSS-TABLE TRIGGER CASE 2 (INVERSE): Active Public Hold Blocks Internal Meeting
# =============================================================================
async def test_inverse_trigger_rejects_internal_meeting_overlapping_active_booking_buffer(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    Tests `trg_meetings_check_booking_conflicts` (`prevent_meeting_overlap_with_bookings`):
    1. A public hold is placed for 10:00 - 10:30 (reserved_range [09:55, 10:40) due to 5m/10m buffers).
    2. Inserting an active busy internal meeting at 10:30 - 11:00 overlaps the [10:30, 10:40) after-buffer
       and must be rejected by PostgreSQL with SQLSTATE 23P01.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    hold_start = (now + timedelta(days=8)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    hold_slot = TimeWindow(hold_start, hold_start + timedelta(minutes=30))

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        active_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=hold_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(active_hold)
        await uow.commit()

    # Attempt to insert an active busy internal meeting at [10:30, 11:00),
    # which overlaps the active booking's reserved_range [09:55, 10:40)
    overlapping_meeting_start = hold_start + timedelta(minutes=30)
    overlapping_meeting_end = hold_start + timedelta(minutes=60)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        with pytest.raises(DBAPIError) as exc_info:
            await uow._session.execute(
                text(
                    """
                    INSERT INTO meetings (
                        id, organization_id, subscription_id, advisor_membership_id,
                        title, meeting_mode, is_busy, organizer_membership_id,
                        scheduled_range, status
                    ) VALUES (
                        :id, :org_id, :sub_id, :adv_id,
                        'Internal Strategy Sync', 'video', TRUE, :adv_id,
                        :scheduled_range, 'active'
                    )
                    """
                ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE)),
                {
                    "id": uuid7(),
                    "org_id": org_id,
                    "sub_id": sub_id,
                    "adv_id": advisor_id,
                    "scheduled_range": Range(
                        overlapping_meeting_start,
                        overlapping_meeting_end,
                        bounds="[)",
                    ),
                },
            )
        assert _is_exclusion_violation(exc_info.value) is True


# =============================================================================
# CROSS-TABLE TRIGGER CASE 3 (INVERSE JIT EVICTION): Internal Meeting Evicts Stale Hold
# =============================================================================
async def test_inverse_trigger_evicts_expired_hold_when_inserting_internal_meeting(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    Tests that `trg_meetings_check_booking_conflicts` automatically flips an overlapping
    expired booking hold (`status = 'HELD' AND hold_expires_at <= now()`) to `EXPIRED`
    when an advisor schedules an active busy internal meeting over that window.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    slot_start = (now + timedelta(days=9)).replace(
        hour=11, minute=0, second=0, microsecond=0
    )
    slot = TimeWindow(slot_start, slot_start + timedelta(minutes=30))

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        stale_hold = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        stale_hold.hold_expires_at = datetime.now(tz=UTC) - timedelta(minutes=2)
        await uow.bookings.add(stale_hold)
        await uow.commit()

    # Insert an active busy internal meeting for the exact same time window
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        assert uow._session is not None
        await uow._session.execute(
            text(
                """
                INSERT INTO meetings (
                    id, organization_id, subscription_id, advisor_membership_id,
                    title, meeting_mode, is_busy, organizer_membership_id,
                    scheduled_range, status
                ) VALUES (
                    :id, :org_id, :sub_id, :adv_id,
                    'Urgent Compliance Review', 'video', TRUE, :adv_id,
                    :scheduled_range, 'active'
                )
                """
            ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE)),
            {
                "id": uuid7(),
                "org_id": org_id,
                "sub_id": sub_id,
                "adv_id": advisor_id,
                "scheduled_range": Range(slot.start_at, slot.end_at, bounds="[)"),
            },
        )
        await uow.commit()

    # Verify the stale hold was flipped to EXPIRED and version incremented
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        evicted = await uow.bookings.get_by_id(org_id, sub_id, stale_hold.id)
        assert evicted is not None
        assert evicted.status == BookingStatus.EXPIRED
        assert evicted.version == stale_hold.version + 1


# =============================================================================
# RLS ISOLATION: Tenant Context Blocks Cross-Tenant Reads and Writes
# =============================================================================
async def test_rls_tenant_isolation_blocks_cross_tenant_reads_and_writes(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    """
    Verifies PostgreSQL Row-Level Security (`tenant_isolation_fence`):
    1. A booking created in Tenant A cannot be read when `app.current_org_id` is set to Tenant B.
    2. Attempting to insert a row for Tenant A while `app.current_org_id` is set to Tenant B
       is rejected by PostgreSQL's RLS `WITH CHECK` policy.
    3. Setting `bypass_rls=True` (`app.bypass_rls = 'on'`) allows background worker visibility.
    """
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    tenant_a_org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    tenant_a_sub_id: UUID = seeded_tenant["sub_id"]  # type: ignore[assignment]
    tenant_b_org_id = uuid7()

    slot_start = (now + timedelta(days=10)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    slot = TimeWindow(slot_start, slot_start + timedelta(minutes=30))

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(tenant_a_org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        booking_a = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(booking_a)
        await uow.commit()

    # 1. Under Tenant B context, Tenant A's booking is invisible even when querying by Tenant A's IDs
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(tenant_b_org_id)
        leaked = await uow.bookings.get_by_id(
            tenant_a_org_id, tenant_a_sub_id, booking_a.id
        )
        assert leaked is None

        # Attempting to update Tenant A's booking under Tenant B context affects 0 rows
        booking_a.meeting_topic = "Unauthorized Cross-Tenant Edit"
        await uow.bookings.save(booking_a)
        await uow.commit()

    # 2. Attempting to INSERT a row with Tenant A's `organization_id` while under Tenant B context
    # violates the RLS `WITH CHECK` policy (SQLSTATE 4250insufficient_privilege)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(tenant_b_org_id)
        non_overlapping_slot = TimeWindow(
            slot_start + timedelta(hours=2),
            slot_start + timedelta(hours=2, minutes=30),
        )
        forged_booking = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=non_overlapping_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        with pytest.raises(DBAPIError) as exc_info:
            await uow.bookings.add(forged_booking)
        assert "row-level security policy" in str(exc_info.value).lower()

    # 3. With `bypass_rls=True`, background workers can read Tenant A's untouched booking
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(tenant_b_org_id, bypass_rls=True)
        visible_with_bypass = await uow.bookings.get_by_id(
            tenant_a_org_id, tenant_a_sub_id, booking_a.id
        )
        assert visible_with_bypass is not None
        assert visible_with_bypass.id == booking_a.id
        assert visible_with_bypass.meeting_topic is None


# =============================================================================
# RESCHEDULE & CANCEL LIFECYCLE: Updates Meeting, Tasks & Frees Busy Window
# =============================================================================
async def test_reschedule_and_cancel_booking_updates_internal_meeting_and_tasks(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_tenant: dict[str, object],
) -> None:
    now: datetime = seeded_tenant["now"]  # type: ignore[assignment]
    public_token: str = seeded_tenant["public_token"]  # type: ignore[assignment]
    org_id: UUID = seeded_tenant["org_id"]  # type: ignore[assignment]
    advisor_id: UUID = seeded_tenant["advisor_id"]  # type: ignore[assignment]

    initial_start = (now + timedelta(days=6)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    initial_slot = TimeWindow(initial_start, initial_start + timedelta(minutes=30))
    rescheduled_start = initial_start + timedelta(hours=2)
    rescheduled_slot = TimeWindow(
        rescheduled_start, rescheduled_start + timedelta(minutes=30)
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        booking = Booking.create_hold(
            booking_link=link,
            meeting_type=meeting_type,
            slot_window=initial_slot,
            prospect_timezone="UTC",
            idempotency_key=f"idem-{uuid7()}",
            now=now,
        )
        await uow.bookings.add(booking)

        (
            prospect_id,
            client_id,
        ) = await uow.bookings.upsert_prospect_and_provision_client(
            organization_id=link.organization_id,
            subscription_id=link.subscription_id,
            advisor_membership_id=meeting_type.advisor_membership_id,
            email="reschedule@example.com",
            full_name="Morgan Client",
            phone=None,
            company_name=None,
        )
        booking.confirm(
            prospect_id=prospect_id,
            client_id=client_id,
            cancel_token_hash=f"hash_{uuid7().hex}",
            meeting_topic="Tax Planning",
            prospect_notes=None,
            now=now + timedelta(seconds=10),
        )
        internal_meeting_id = await uow.bookings.create_internal_meeting(
            booking=booking,
            meeting_type=meeting_type,
            prospect_full_name="Morgan Client",
            prospect_email="reschedule@example.com",
        )
        await uow.bookings.save(booking)
        await uow.commit()

    # Reschedule confirmed booking and its linked internal meeting
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        assert resolved is not None
        link, meeting_type, _ = resolved

        saved = await uow.bookings.get_by_id(
            org_id, link.subscription_id, booking.id, for_update=True
        )
        assert saved is not None
        assert saved.internal_meeting_id == internal_meeting_id

        saved.reschedule(
            new_slot_window=rescheduled_slot,
            meeting_type=meeting_type,
            now=now + timedelta(minutes=1),
        )
        await uow.bookings.update_internal_meeting_schedule(
            organization_id=org_id,
            subscription_id=link.subscription_id,
            internal_meeting_id=internal_meeting_id,
            new_slot=rescheduled_slot,
        )
        await uow.bookings.save(saved)
        await uow.commit()

    # Cancel booking and verify busy windows are cleared
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        saved = await uow.bookings.get_by_id(
            org_id, link.subscription_id, booking.id, for_update=True
        )
        assert saved is not None
        assert saved.slot_window == rescheduled_slot

        saved.cancel(
            reason="Client requested cancellation",
            now=now + timedelta(minutes=2),
        )
        await uow.bookings.save(saved)
        await uow.bookings.cancel_internal_meeting(
            organization_id=org_id,
            subscription_id=link.subscription_id,
            internal_meeting_id=internal_meeting_id,
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.set_tenant_context(org_id)
        busy_windows = await uow.schedules.get_opaque_busy_windows(
            organization_id=org_id,
            advisor_membership_id=advisor_id,
            search_window=TimeWindow(
                initial_start - timedelta(hours=1),
                rescheduled_start + timedelta(hours=2),
            ),
            now=now + timedelta(minutes=3),
        )
        assert busy_windows == []
