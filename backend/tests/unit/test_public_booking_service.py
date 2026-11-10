# 50% or more AI-generated code

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

from app.domain.entities import (
    AvailabilityOverride,
    AvailabilityRule,
    Booking,
    MeetingType,
    PublicBookingLink,
)
from app.domain.enums import BookingStatus, MeetingMode
from app.domain.exceptions import (
    BookingLinkInvalidError,
    HoldExpiredError,
    InvalidCancellationTokenError,
    InvalidSlotSelectionError,
    SlotOverlapConflictError,
)
from app.domain.repositories import (
    AbstractBookingRepository,
    AbstractScheduleRepository,
)
from app.domain.structs import BufferConfig, TimeWindow
from app.domain.uow import AbstractUnitOfWork
from app.services.public_booking import PublicBookingService, hash_cancel_token

NY_TZ = ZoneInfo("America/New_York")


# =============================================================================
# In-Memory Fake Repositories & FakeUnitOfWork
#    Simulates PostgreSQL tables, GiST overlap checks, and RLS context in RAM!
# =============================================================================


class FakeScheduleRepository(AbstractScheduleRepository):
    def __init__(self, bookings_store: dict[UUID, Booking]) -> None:
        self.links: dict[str, tuple[PublicBookingLink, MeetingType, str]] = {}
        self.rules: list[AvailabilityRule] = []
        self.overrides: list[AvailabilityOverride] = []
        self.internal_busy_meetings: list[tuple[UUID, TimeWindow]] = []
        self._bookings_store = bookings_store

    async def get_active_booking_link(
        self, public_token: str, now: datetime
    ) -> tuple[PublicBookingLink, MeetingType, str] | None:
        entry = self.links.get(public_token)
        if entry is None:
            return None
        link, mt, advisor_name = entry
        if not link.is_active or link.expires_at <= now or not mt.is_active:
            return None
        return link, mt, advisor_name

    async def get_advisor_rules(
        self, organization_id: UUID, advisor_membership_id: UUID
    ) -> list[AvailabilityRule]:
        return [
            r
            for r in self.rules
            if r.organization_id == organization_id
            and r.advisor_membership_id == advisor_membership_id
            and r.is_active
        ]

    async def get_advisor_overrides(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[AvailabilityOverride]:
        return [
            ov
            for ov in self.overrides
            if ov.organization_id == organization_id
            and ov.advisor_membership_id == advisor_membership_id
            and start_date <= ov.override_date <= end_date
        ]

    async def get_opaque_busy_windows(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        search_window: TimeWindow,
        now: datetime,
        exclude_booking_id: UUID | None = None,
    ) -> list[TimeWindow]:
        busy: list[TimeWindow] = []
        for b in self._bookings_store.values():
            if (
                b.organization_id != organization_id
                or b.advisor_membership_id != advisor_membership_id
            ):
                continue
            if exclude_booking_id is not None and b.id == exclude_booking_id:
                continue
            is_active = b.status == BookingStatus.CONFIRMED or (
                b.status == BookingStatus.HELD
                and b.hold_expires_at is not None
                and b.hold_expires_at > now
            )
            if is_active and b.reserved_window.overlaps(search_window):
                busy.append(b.reserved_window)

        for meeting_id, window in self.internal_busy_meetings:
            if window.overlaps(search_window):
                busy.append(window)

        return busy


class FakeBookingRepository(AbstractBookingRepository):
    def __init__(self) -> None:
        self.bookings: dict[UUID, Booking] = {}
        self.cancelled_meetings: list[UUID] = []
        self.rescheduled_meetings: dict[UUID, TimeWindow] = {}

    async def get_by_id(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        booking_id: UUID,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        b = self.bookings.get(booking_id)
        if (
            b
            and b.organization_id == organization_id
            and b.subscription_id == subscription_id
        ):
            return b
        return None

    async def get_by_idempotency_key(
        self, organization_id: UUID, idempotency_key: str
    ) -> Booking | None:
        for b in self.bookings.values():
            if (
                b.organization_id == organization_id
                and b.idempotency_key == idempotency_key
            ):
                return b
        return None

    async def get_by_cancel_token_hash(
        self, cancel_token_hash: str, *, for_update: bool = False
    ) -> Booking | None:
        for b in self.bookings.values():
            if b.cancel_token_hash == cancel_token_hash:
                return b
        return None

    async def add(self, booking: Booking) -> None:
        # Simulate PostgreSQL GiST exclusion constraint on active bookings
        for existing in self.bookings.values():
            if (
                existing.organization_id == booking.organization_id
                and existing.advisor_membership_id == booking.advisor_membership_id
                and existing.status in (BookingStatus.HELD, BookingStatus.CONFIRMED)
                and existing.reserved_window.overlaps(booking.reserved_window)
            ):
                raise SlotOverlapConflictError("Simulated GiST 23P01 overlap conflict.")
        self.bookings[booking.id] = booking

    async def save(self, booking: Booking) -> None:
        for existing in self.bookings.values():
            if (
                existing.id != booking.id
                and existing.organization_id == booking.organization_id
                and existing.advisor_membership_id == booking.advisor_membership_id
                and booking.status in (BookingStatus.HELD, BookingStatus.CONFIRMED)
                and existing.status in (BookingStatus.HELD, BookingStatus.CONFIRMED)
                and existing.reserved_window.overlaps(booking.reserved_window)
            ):
                raise SlotOverlapConflictError(
                    "Simulated GiST 23P01 overlap on update."
                )
        self.bookings[booking.id] = booking

    async def upsert_prospect_and_provision_client(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        advisor_membership_id: UUID,
        email: str,
        full_name: str,
        phone: str | None,
        company_name: str | None,
    ) -> tuple[UUID, UUID]:
        return uuid4(), uuid4()

    async def create_internal_meeting(
        self,
        *,
        booking: Booking,
        meeting_type: MeetingType,
        prospect_full_name: str,
        prospect_email: str,
    ) -> UUID:
        return uuid4()

    async def update_internal_meeting_schedule(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
        new_slot: TimeWindow,
    ) -> None:
        self.rescheduled_meetings[internal_meeting_id] = new_slot

    async def cancel_internal_meeting(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
    ) -> None:
        self.cancelled_meetings.append(internal_meeting_id)


class FakeUnitOfWork(AbstractUnitOfWork):
    schedules: FakeScheduleRepository
    bookings: FakeBookingRepository

    def __init__(self) -> None:
        self.bookings = FakeBookingRepository()
        self.schedules = FakeScheduleRepository(self.bookings.bookings)
        self.committed = False
        self.rolled_back = False
        self.current_org_id: UUID | None = None
        self.bypass_rls: bool = False

    async def set_tenant_context(
        self,
        organization_id: UUID | None,
        *,
        bypass_rls: bool = False,
    ) -> None:
        self.current_org_id = organization_id
        self.bypass_rls = bypass_rls

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


# =============================================================================
# Shared Test Fixtures
# =============================================================================


@pytest.fixture
def now() -> datetime:
    """Sunday, Nov 1, 2026 at 12:00 UTC."""
    return datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow(now: datetime) -> FakeUnitOfWork:
    """Pre-seeds a FakeUnitOfWork with an active Advisor, Monday 09:00-11:00 rule, and BookingLink."""
    fake_uow = FakeUnitOfWork()
    org_id = uuid4()
    sub_id = uuid4()
    advisor_id = uuid4()

    rule = AvailabilityRule(
        id=uuid4(),
        organization_id=org_id,
        advisor_membership_id=advisor_id,
        day_of_week=1,  # Monday
        start_time=time(9, 0),
        end_time=time(11, 0),
        timezone="America/New_York",
        valid_from=date(2026, 1, 1),
    )
    mt = MeetingType(
        id=uuid4(),
        organization_id=org_id,
        subscription_id=sub_id,
        advisor_membership_id=advisor_id,
        slug="wealth-review",
        title="30-Min Wealth Review",
        description=None,
        duration_minutes=30,
        slot_interval_minutes=30,
        buffers=BufferConfig(before_minutes=5, after_minutes=10),
        minimum_notice_minutes=60,
        max_days_in_advance=60,
        meeting_mode=MeetingMode.VIDEO,
    )
    link = PublicBookingLink(
        id=uuid4(),
        organization_id=org_id,
        subscription_id=sub_id,
        organizer_membership_id=advisor_id,
        advisor_membership_id=advisor_id,
        meeting_type_id=mt.id,
        public_token="tok_valid_123",
        title="Book with Jane Doe",
        is_active=True,
        expires_at=now + timedelta(days=30),
        hold_ttl_seconds=300,
    )

    fake_uow.schedules.rules.append(rule)
    fake_uow.schedules.links["tok_valid_123"] = (link, mt, "Jane Doe, CFA")
    return fake_uow


@pytest.fixture
def monday_9am_slot() -> TimeWindow:
    """Monday, Nov 2, 2026 from 09:00 to 09:30 America/New_York."""
    return TimeWindow(
        datetime(2026, 11, 2, 9, 0, tzinfo=NY_TZ),
        datetime(2026, 11, 2, 9, 30, tzinfo=NY_TZ),
    )


@pytest.fixture
def monday_10am_slot() -> TimeWindow:
    """Monday, Nov 2, 2026 from 10:00 to 10:30 America/New_York."""
    return TimeWindow(
        datetime(2026, 11, 2, 10, 0, tzinfo=NY_TZ),
        datetime(2026, 11, 2, 10, 30, tzinfo=NY_TZ),
    )


# =============================================================================
# HAPPY PATH TESTS (Query -> Hold -> Confirm -> Reschedule -> Cancel)
# =============================================================================


async def test_happy_path_weekly_and_monthly_availability(
    uow: FakeUnitOfWork, now: datetime
) -> None:
    """Service resolves public_token, locks RLS to the organization, and returns open slots."""
    service = PublicBookingService(uow)

    weekly = await service.get_weekly_availability(
        public_token="tok_valid_123",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 8),
        now=now,
    )
    assert weekly.advisor_display_name == "Jane Doe, CFA"
    assert len(weekly.slots) == 4  # 9:00, 9:30, 10:00, 10:30 on Monday Nov 2
    assert uow.bypass_rls is False
    assert uow.current_org_id == weekly.meeting_type.organization_id

    monthly = await service.get_monthly_availability(
        public_token="tok_valid_123",
        year=2026,
        month=11,
        viewer_timezone="America/New_York",
        now=now,
    )
    assert len(monthly.days) == 30
    assert monthly.days[1].total_available_slots == 4  # Nov 2 (Monday)


async def test_happy_path_hold_then_confirm_hashes_token(
    uow: FakeUnitOfWork,
    monday_9am_slot: TimeWindow,
    now: datetime,
) -> None:
    """
    Holding and confirming a slot:
    1. Transitions status HELD -> CONFIRMED.
    2. Stores ONLY the SHA-256 hash in `booking.cancel_token_hash` (never the raw token).
    """
    service = PublicBookingService(uow)

    # Step 1: Acquire soft hold
    held = await service.acquire_slot_hold(
        public_token="tok_valid_123",
        slot_window=monday_9am_slot,
        prospect_timezone="America/New_York",
        idempotency_key="idem-hold-1",
        now=now,
    )
    assert held.status == BookingStatus.HELD

    # Step 2: Confirm hold
    confirmed_result = await service.confirm_booking(
        public_token="tok_valid_123",
        booking_id=held.id,
        email="Client@Example.com",
        full_name="Sam Client",
        phone="+15145550100",
        company_name="Sam Co",
        meeting_topic="Estate Planning",
        prospect_notes="First meeting",
        now=now + timedelta(minutes=1),
    )

    booking = confirmed_result.booking
    raw_token = confirmed_result.cancel_token

    assert booking.status == BookingStatus.CONFIRMED
    assert booking.hold_expires_at is None
    # Security invariant: DB stores SHA-256 hash, never raw token!
    assert booking.cancel_token_hash != raw_token
    assert booking.cancel_token_hash == hash_cancel_token(raw_token)


async def test_happy_path_reschedule_and_cancel_with_raw_token(
    uow: FakeUnitOfWork,
    monday_9am_slot: TimeWindow,
    monday_10am_slot: TimeWindow,
    now: datetime,
) -> None:
    """A prospect can reschedule to a new open slot and later cancel using their raw `cancel_token`."""
    service = PublicBookingService(uow)

    held = await service.acquire_slot_hold(
        public_token="tok_valid_123",
        slot_window=monday_9am_slot,
        prospect_timezone="America/New_York",
        idempotency_key="idem-hold-2",
        now=now,
    )
    confirmed = await service.confirm_booking(
        public_token="tok_valid_123",
        booking_id=held.id,
        email="sam@example.com",
        full_name="Sam Client",
        now=now + timedelta(minutes=1),
    )

    # Reschedule from 09:00 to 10:00
    rescheduled = await service.reschedule_booking(
        public_token="tok_valid_123",
        raw_cancel_token=confirmed.cancel_token,
        new_slot_window=monday_10am_slot,
        now=now + timedelta(minutes=5),
    )
    assert rescheduled.slot_window == monday_10am_slot
    assert rescheduled.internal_meeting_id in uow.bookings.rescheduled_meetings

    # Cancel booking
    cancelled = await service.cancel_booking(
        raw_cancel_token=confirmed.cancel_token,
        reason="Need to travel",
        now=now + timedelta(minutes=10),
    )
    assert cancelled.status == BookingStatus.CANCELLED
    assert cancelled.internal_meeting_id in uow.bookings.cancelled_meetings


# =============================================================================
# EDGE & IDEMPOTENCY CASES
# =============================================================================


async def test_edge_idempotent_hold_retry_returns_existing_hold_without_conflict(
    uow: FakeUnitOfWork,
    monday_9am_slot: TimeWindow,
    now: datetime,
) -> None:
    """Repeating `acquire_slot_hold` with the same `idempotency_key` returns the original hold instead of raising 409."""
    service = PublicBookingService(uow)

    first = await service.acquire_slot_hold(
        public_token="tok_valid_123",
        slot_window=monday_9am_slot,
        prospect_timezone="UTC",
        idempotency_key="retry-key-99",
        now=now,
    )
    second = await service.acquire_slot_hold(
        public_token="tok_valid_123",
        slot_window=monday_9am_slot,
        prospect_timezone="UTC",
        idempotency_key="retry-key-99",
        now=now + timedelta(seconds=2),
    )

    assert first.id == second.id


# =============================================================================
# FAILURE, CONCURRENCY & SECURITY CASES
# =============================================================================


async def test_failure_booking_slot_outside_working_hours_is_rejected(
    uow: FakeUnitOfWork,
    now: datetime,
) -> None:
    """Attempting to hold a slot at 3:00 AM (when advisor works 9:00-11:00) raises InvalidSlotSelectionError."""
    service = PublicBookingService(uow)
    sunday_3am_slot = TimeWindow(
        datetime(2026, 11, 2, 3, 0, tzinfo=NY_TZ),
        datetime(2026, 11, 2, 3, 30, tzinfo=NY_TZ),
    )

    with pytest.raises(
        InvalidSlotSelectionError, match="outside the advisor's available schedule"
    ):
        await service.acquire_slot_hold(
            public_token="tok_valid_123",
            slot_window=sunday_3am_slot,
            prospect_timezone="UTC",
            idempotency_key="idem-bad-hour",
            now=now,
        )


async def test_failure_confirming_expired_hold_marks_booking_expired_and_raises(
    uow: FakeUnitOfWork,
    monday_9am_slot: TimeWindow,
    now: datetime,
) -> None:
    """If a user submits the confirmation form after the 5-minute TTL, status becomes EXPIRED and HoldExpiredError is raised."""
    service = PublicBookingService(uow)

    held = await service.acquire_slot_hold(
        public_token="tok_valid_123",
        slot_window=monday_9am_slot,
        prospect_timezone="UTC",
        idempotency_key="idem-expire",
        now=now,
    )

    with pytest.raises(HoldExpiredError, match="expired"):
        await service.confirm_booking(
            public_token="tok_valid_123",
            booking_id=held.id,
            email="late@example.com",
            full_name="Late User",
            now=now + timedelta(minutes=6),  # 1 minute past the 300s TTL!
        )

    assert held.status == BookingStatus.EXPIRED


async def test_failure_unknown_public_token_or_cancel_token_raises(
    uow: FakeUnitOfWork,
    now: datetime,
) -> None:
    """Invalid tokens are rejected before any tenant data can be accessed."""
    service = PublicBookingService(uow)

    with pytest.raises(BookingLinkInvalidError):
        await service.get_weekly_availability(
            public_token="tok_does_not_exist",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 8),
            now=now,
        )

    with pytest.raises(InvalidCancellationTokenError):
        await service.cancel_booking(
            raw_cancel_token="forged_or_wrong_token",
            reason="Test",
            now=now,
        )
