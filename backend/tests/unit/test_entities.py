# 50% or more AI-generated code
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid7

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
    InvalidTimeWindowError,
)
from app.domain.structs import BufferConfig, TimeWindow


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


@pytest.fixture
def tenant_ids() -> dict[str, UUID]:
    return {
        "org_id": uuid7(),
        "sub_id": uuid7(),
        "advisor_id": uuid7(),
        "organizer_id": uuid7(),
    }


@pytest.fixture
def meeting_type(tenant_ids: dict[str, object]) -> MeetingType:
    """30min video consultation with 5m before / 10m after buffers."""
    return MeetingType(
        id=uuid7(),
        organization_id=tenant_ids["org_id"],  # type: ignore[arg-type]
        subscription_id=tenant_ids["sub_id"],  # type: ignore[arg-type]
        advisor_membership_id=tenant_ids["advisor_id"],  # type: ignore[arg-type]
        slug="initial-consultation",
        title="30-Min Initial Consultation",
        description="Introductory wealth planning session",
        duration_minutes=30,
        slot_interval_minutes=15,
        buffers=BufferConfig(before_minutes=5, after_minutes=10),
        minimum_notice_minutes=60,
        max_days_in_advance=60,
        meeting_mode=MeetingMode.VIDEO,
    )


@pytest.fixture
def booking_link(
    tenant_ids: dict[str, object], meeting_type: MeetingType, now: datetime
) -> PublicBookingLink:
    """active public booking link valid for 30d with a 5m TTL"""
    return PublicBookingLink(
        id=uuid7(),
        organization_id=meeting_type.organization_id,
        subscription_id=meeting_type.subscription_id,
        organizer_membership_id=tenant_ids["organizer_id"],  # type: ignore[arg-type]
        advisor_membership_id=meeting_type.advisor_membership_id,
        meeting_type_id=meeting_type.id,
        public_token="tok_public_12345",
        title="Book with Advisor",
        is_active=True,
        expires_at=now + timedelta(days=30),
        hold_ttl_seconds=300,
    )


@pytest.fixture
def valid_slot(now: datetime) -> TimeWindow:
    """30m slot starting 24 hours from now (outside minimum notice)"""
    start = now + timedelta(days=1)
    return TimeWindow(start_at=start, end_at=start + timedelta(minutes=30))


# =============================================================================
# vailabilityRule & AvailabilityOverride Tests
# =============================================================================


def test_availability_rule_validation() -> None:
    org_id, advisor_id = uuid7(), uuid7()

    # valid rule passes
    rule = AvailabilityRule(
        id=uuid7(),
        organization_id=org_id,
        advisor_membership_id=advisor_id,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone="America/New_York",
    )
    assert rule.day_of_week == 1

    # invalid day_of_week raises
    with pytest.raises(ValueError, match="day_of_week"):
        AvailabilityRule(
            id=uuid7(),
            organization_id=org_id,
            advisor_membership_id=advisor_id,
            day_of_week=7,
            start_time=time(9, 0),
            end_time=time(17, 0),
            timezone="America/New_York",
        )

    # end_time <= start_time raises
    with pytest.raises(InvalidTimeWindowError, match="end_time"):
        AvailabilityRule(
            id=uuid7(),
            organization_id=org_id,
            advisor_membership_id=advisor_id,
            day_of_week=1,
            start_time=time(17, 0),
            end_time=time(9, 0),
            timezone="America/New_York",
        )


def test_availability_override_requires_window_when_available() -> None:
    with pytest.raises(ValueError, match="custom_window"):
        AvailabilityOverride(
            id=uuid7(),
            organization_id=uuid7(),
            advisor_membership_id=uuid7(),
            override_date=date(2026, 11, 15),
            is_available=True,
            custom_window=None,
        )


# =============================================================================
# MeetingType Validation Tests
# =============================================================================


def test_meeting_type_rejects_wrong_duration(
    meeting_type: MeetingType, now: datetime
) -> None:
    # 60m slot instead of 30m
    start = now + timedelta(days=1)
    wrong_duration_slot = TimeWindow(start, start + timedelta(minutes=60))

    with pytest.raises(InvalidSlotSelectionError, match="duration"):
        meeting_type.validate_requested_slot(wrong_duration_slot, now)


def test_meeting_type_rejects_too_soon_notice(
    meeting_type: MeetingType, now: datetime
) -> None:
    # starts in 30 minutes, but minimum_notice_minutes is 60
    start = now + timedelta(minutes=30)
    too_soon_slot = TimeWindow(start, start + timedelta(minutes=30))

    with pytest.raises(InvalidSlotSelectionError, match="minimum advance notice"):
        meeting_type.validate_requested_slot(too_soon_slot, now)


def test_meeting_type_rejects_too_far_in_advance(
    meeting_type: MeetingType, now: datetime
) -> None:
    # starts in 90d, but max_days_in_advance is 60
    start = now + timedelta(days=90)
    too_far_slot = TimeWindow(start, start + timedelta(minutes=30))

    with pytest.raises(InvalidSlotSelectionError, match="maximum advance"):
        meeting_type.validate_requested_slot(too_far_slot, now)


# =============================================================================
# Booking Tests (HELD -> CONFIRMED -> RESCHEDULED -> CANCELLED)
# =============================================================================


def test_create_hold_populates_fields_and_expands_buffers(
    booking_link: PublicBookingLink,
    meeting_type: MeetingType,
    valid_slot: TimeWindow,
    now: datetime,
) -> None:
    booking = Booking.create_hold(
        booking_link=booking_link,
        meeting_type=meeting_type,
        slot_window=valid_slot,
        prospect_timezone="America/Toronto",
        idempotency_key="idem-001",
        now=now,
    )

    assert booking.status == BookingStatus.HELD
    assert booking.hold_expires_at == now + timedelta(seconds=300)
    assert booking.slot_window == valid_slot
    assert booking.reserved_window == TimeWindow(
        valid_slot.start_at - timedelta(minutes=5),
        valid_slot.end_at + timedelta(minutes=10),
    )


def test_create_hold_rejects_expired_booking_link(
    booking_link: PublicBookingLink,
    meeting_type: MeetingType,
    valid_slot: TimeWindow,
    now: datetime,
) -> None:
    # expire the link 1 minute ago
    booking_link.expires_at = now - timedelta(minutes=1)

    with pytest.raises(BookingLinkInvalidError, match="expired"):
        Booking.create_hold(
            booking_link=booking_link,
            meeting_type=meeting_type,
            slot_window=valid_slot,
            prospect_timezone="UTC",
            idempotency_key="idem-002",
            now=now,
        )


def test_confirm_booking_succeeds_before_hold_expiration(
    booking_link: PublicBookingLink,
    meeting_type: MeetingType,
    valid_slot: TimeWindow,
    now: datetime,
) -> None:
    booking = Booking.create_hold(
        booking_link=booking_link,
        meeting_type=meeting_type,
        slot_window=valid_slot,
        prospect_timezone="UTC",
        idempotency_key="idem-003",
        now=now,
    )
    prospect_id, client_id, meeting_id = uuid7(), uuid7(), uuid7()

    # confirm 2m after hold was created, within TTL
    booking.confirm(
        prospect_id=prospect_id,
        client_id=client_id,
        internal_meeting_id=meeting_id,
        cancel_token_hash="sha256_secret_hash",
        meeting_topic="Retirement Planning",
        prospect_notes="Looking to roll over 401k",
        now=now + timedelta(minutes=2),
    )

    assert booking.status == BookingStatus.CONFIRMED
    assert booking.hold_expires_at is None
    assert booking.prospect_id == prospect_id
    assert booking.client_id == client_id
    assert booking.internal_meeting_id == meeting_id
    assert booking.cancel_token_hash == "sha256_secret_hash"
    assert booking.version == 2


def test_confirm_booking_fails_when_hold_expired(
    booking_link: PublicBookingLink,
    meeting_type: MeetingType,
    valid_slot: TimeWindow,
    now: datetime,
) -> None:
    booking = Booking.create_hold(
        booking_link=booking_link,
        meeting_type=meeting_type,
        slot_window=valid_slot,
        prospect_timezone="UTC",
        idempotency_key="idem-004",
        now=now,
    )

    # attempt to confirm 6 minutes later, after TTL
    with pytest.raises(HoldExpiredError, match="expired"):
        booking.confirm(
            prospect_id=uuid7(),
            client_id=uuid7(),
            internal_meeting_id=uuid7(),
            cancel_token_hash="sha256_secret_hash",
            meeting_topic=None,
            prospect_notes=None,
            now=now + timedelta(minutes=6),
        )
    assert booking.status == BookingStatus.EXPIRED


def test_reschedule_and_cancel_confirmed_booking(
    booking_link: PublicBookingLink,
    meeting_type: MeetingType,
    valid_slot: TimeWindow,
    now: datetime,
) -> None:
    booking = Booking.create_hold(
        booking_link=booking_link,
        meeting_type=meeting_type,
        slot_window=valid_slot,
        prospect_timezone="UTC",
        idempotency_key="idem-005",
        now=now,
    )
    booking.confirm(
        prospect_id=uuid7(),
        client_id=uuid7(),
        internal_meeting_id=uuid7(),
        cancel_token_hash="sha256_secret_hash",
        meeting_topic="Tax Review",
        prospect_notes=None,
        now=now + timedelta(minutes=1),
    )

    # reschedule in 2d
    new_start = now + timedelta(days=2)
    new_slot = TimeWindow(new_start, new_start + timedelta(minutes=30))
    booking.reschedule(new_slot_window=new_slot, meeting_type=meeting_type, now=now)

    # slot and buffer-expanded reserved_window both updated
    assert booking.slot_window == new_slot
    assert booking.reserved_window == meeting_type.buffers.expand(new_slot)
    assert booking.version == 3

    # cancel the booking
    cancel_time = now + timedelta(hours=2)
    booking.cancel(reason="Schedule conflict", now=cancel_time)

    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at == cancel_time
    assert booking.cancellation_reason == "Schedule conflict"
    assert booking.version == 4

    # cancelling again  raises
    with pytest.raises(InvalidCancellationTokenError):
        booking.cancel(reason="Duplicate cancel", now=cancel_time)
