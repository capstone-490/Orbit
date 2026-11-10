# Below 50% AI-generated code
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from uuid import UUID, uuid7

from app.domain.enums import BookingStatus, ClientStatus, MeetingMode, OnboardingStage
from app.domain.exceptions import (
    BookingLinkInvalidError,
    HoldExpiredError,
    InvalidCancellationTokenError,
    InvalidSlotSelectionError,
    InvalidTimeWindowError,
)
from app.domain.structs import BufferConfig, TimeWindow


@dataclass(slots=True)
class AvailabilityRule:
    "Store weekly hours of an advisor."

    id: UUID
    organization_id: UUID
    advisor_membership_id: UUID
    day_of_week: int  # 0 = Sunday .. 6 = Saturday
    start_time: time
    end_time: time
    timezone: str  # IANA timezone string, e.g. "America/New_York"
    is_active: bool = True
    valid_from: date = field(default_factory=date.today)
    valid_until: date | None = None

    def __post_init__(self) -> None:
        # make sure the day number is within the allowed range
        if not (0 <= self.day_of_week <= 6):
            raise ValueError(
                "Invalid day_of_week: must be between 0 (Sunday) and 6 (Saturday)."
            )

        # end time after start time
        if self.end_time <= self.start_time:
            raise InvalidTimeWindowError("end_time must be strictly after start_time.")

        # dont allow the rule to expire before it even starts
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot be earlier than valid_from.")


@dataclass(slots=True)
class AvailabilityOverride:
    """Stores advisor custom ovverides to availability for a date."""

    id: UUID
    organization_id: UUID
    advisor_membership_id: UUID
    override_date: date
    is_available: bool = False
    custom_window: TimeWindow | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        # if marked available, a custom time range must be provided
        if self.is_available is True and self.custom_window is None:
            raise ValueError("An available override must specify a custom_window.")


@dataclass(slots=True)
class MeetingType:
    """Store the settings for a type of meeting that can be booked"""

    id: UUID
    organization_id: UUID
    subscription_id: UUID
    advisor_membership_id: UUID
    slug: str
    title: str
    description: str | None
    duration_minutes: int
    slot_interval_minutes: int
    buffers: BufferConfig
    minimum_notice_minutes: int
    max_days_in_advance: int
    meeting_mode: MeetingMode
    pre_meeting_agent_id: UUID | None = None
    is_active: bool = True

    def validate_requested_slot(
        self,
        slot: TimeWindow,
        now: datetime,
    ) -> None:

        # check slot matches this meetings duration
        if self.duration_minutes != slot.duration_minutes:
            raise InvalidSlotSelectionError(
                "Meeting type does not fit within slot.duration_minutes."
            )

        # calculate the earliest time someone is allowed to book
        earliest_allowed_start = now + timedelta(minutes=self.minimum_notice_minutes)
        if slot.start_at < earliest_allowed_start:
            raise InvalidSlotSelectionError(
                "Slot violates minimum advance notice requirement."
            )

        # calculate the furthest date someone can book ahead
        latest_allowed_start = now + timedelta(days=self.max_days_in_advance)
        if slot.start_at > latest_allowed_start:
            raise InvalidSlotSelectionError(
                "Slot exceeds maximum advance booking window."
            )


@dataclass(slots=True)
class PublicBookingLink:
    """Store the info needed to let someone book through a public link"""

    id: UUID
    organization_id: UUID
    subscription_id: UUID
    organizer_membership_id: UUID
    advisor_membership_id: UUID | None
    meeting_type_id: UUID | None
    public_token: str
    title: str
    is_active: bool
    expires_at: datetime
    hold_ttl_seconds: int = 300

    def validate_usable(self, now: datetime) -> None:
        if not self.is_active or self.expires_at <= now:
            raise BookingLinkInvalidError("Booking link is invalid or has expired.")

        # a booking link needs an advisor and meeting type
        if self.advisor_membership_id is None or self.meeting_type_id is None:
            raise BookingLinkInvalidError(
                "Booking link requires an advisor and meeting type."
            )


@dataclass(slots=True)
class Booking:
    """Describes an appointment."""

    id: UUID
    organization_id: UUID
    subscription_id: UUID
    advisor_membership_id: UUID
    booking_link_id: UUID
    meeting_type_id: UUID
    status: BookingStatus
    slot_window: TimeWindow
    reserved_window: TimeWindow
    prospect_timezone: str
    idempotency_key: str
    prospect_id: UUID | None = None
    client_id: UUID | None = None
    internal_meeting_id: UUID | None = None
    meeting_topic: str | None = None
    prospect_notes: str | None = None
    hold_expires_at: datetime | None = None
    cancel_token_hash: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    rescheduled_from_id: UUID | None = None
    version: int = 1

    @classmethod
    def create_hold(
        cls,
        *,
        booking_link: PublicBookingLink,
        meeting_type: MeetingType,
        slot_window: TimeWindow,
        prospect_timezone: str,
        idempotency_key: str,
        now: datetime,
    ) -> Booking:
        # check the link and requested meeting time are valid
        booking_link.validate_usable(now)
        meeting_type.validate_requested_slot(slot_window, now)

        # expand the slot to include buffer time
        reserved_window = meeting_type.buffers.expand(slot_window)
        # set the temporary booking hold expiration time
        hold_expires_at = now + timedelta(seconds=booking_link.hold_ttl_seconds)
        # create a new booking with a held status
        return cls(
            id=uuid7(),
            organization_id=booking_link.organization_id,
            subscription_id=booking_link.subscription_id,
            advisor_membership_id=meeting_type.advisor_membership_id,
            booking_link_id=booking_link.id,
            meeting_type_id=meeting_type.id,
            status=BookingStatus.HELD,
            slot_window=slot_window,
            reserved_window=reserved_window,
            prospect_timezone=prospect_timezone,
            idempotency_key=idempotency_key,
            hold_expires_at=hold_expires_at,
            version=1,
        )

    def confirm(
        self,
        *,
        prospect_id: UUID | None = None,
        client_id: UUID | None = None,
        internal_meeting_id: UUID | None = None,
        cancel_token_hash: str,
        meeting_topic: str | None = None,
        prospect_notes: str | None = None,
        now: datetime,
    ) -> None:
        # only holds can be confirmed
        if self.status != BookingStatus.HELD:
            raise HoldExpiredError("Unable to confirm booking, status is not HELD.")
        if self.hold_expires_at is None or self.hold_expires_at <= now:
            self.status = BookingStatus.EXPIRED
            raise HoldExpiredError("Hold has expired.")

        # require a token hash so the booking can be cancelled later
        if not cancel_token_hash:
            raise ValueError("cancel_token_hash is required to confirm a booking.")

        # link the booking to a prospect or existing client
        if prospect_id is None and client_id is None:
            raise ValueError(
                "A confirmed booking requires at least a prospect_id or client_id."
            )

        # transition to confirmed
        self.status = BookingStatus.CONFIRMED
        self.hold_expires_at = None
        self.prospect_id = prospect_id
        self.client_id = client_id
        if internal_meeting_id is not None:
            self.internal_meeting_id = internal_meeting_id
        self.cancel_token_hash = cancel_token_hash
        self.meeting_topic = meeting_topic
        self.prospect_notes = prospect_notes

        # increase version whenever the booking changes
        self.version += 1

    def cancel(
        self,
        *,
        reason: str | None,
        now: datetime,
    ) -> None:
        # cannot cancel something already cancelled or expired
        if self.status in (BookingStatus.CANCELLED, BookingStatus.EXPIRED):
            raise InvalidCancellationTokenError(
                "Booking is already cancelled or expired."
            )
        self.status = BookingStatus.CANCELLED
        self.hold_expires_at = None
        self.cancelled_at = now
        self.cancellation_reason = reason
        self.version += 1

    def reschedule(
        self,
        *,
        new_slot_window: TimeWindow,
        meeting_type: MeetingType,
        now: datetime,
    ) -> None:

        # only confirmed bookings can be moved to another time
        if self.status != BookingStatus.CONFIRMED:
            raise InvalidCancellationTokenError(
                "Only confirmed bookings can be rescheduled."
            )
        meeting_type.validate_requested_slot(new_slot_window, now)
        self.slot_window = new_slot_window
        self.reserved_window = meeting_type.buffers.expand(new_slot_window)
        self.version += 1


@dataclass(slots=True)
class Client:
    """Describes an advisor client"""

    id: UUID
    organization_id: UUID
    subscription_id: UUID
    display_name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    occupation: str | None = None
    onboarding_stage: OnboardingStage | None = None
    primary_advisor_membership_id: UUID | None = None
    status: ClientStatus = ClientStatus.PROVISIONING
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.display_name = self.display_name.strip()
        if not self.display_name:
            raise ValueError("Client display_name cannot be empty.")

        if self.email is not None:
            self.email = self.email.strip().lower() or None

        if self.date_of_birth is not None and (
            self.date_of_birth < date(1900, 1, 1) or self.date_of_birth > date.today()
        ):
            raise ValueError(
                "Client date_of_birth must be between 1900-01-01 and today."
            )

        # enforce deleted status matches the deleted timestamp
        if (self.status == ClientStatus.DELETED) != (self.deleted_at is not None):
            raise ValueError(
                "Client status='deleted' requires deleted_at timestamp (and vice versa)."
            )

    def calculate_age(self, today: date | None = None) -> int | None:
        """Dynamically computes client's current age in years from date_of_birth."""
        if self.date_of_birth is None:
            return None
        ref_date = today or date.today()

        # subtract birth year from current year
        # then check if the birthday already happened this year
        return (
            ref_date.year
            - self.date_of_birth.year
            - (
                (ref_date.month, ref_date.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def soft_delete(self, *, now: datetime) -> None:
        # mark as deleted without removing the client record
        self.status = ClientStatus.DELETED
        self.deleted_at = now
