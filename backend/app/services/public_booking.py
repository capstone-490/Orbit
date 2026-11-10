# 50 or more AI-generated code
from __future__ import annotations

import calendar
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from app.domain.entities import Booking, MeetingType, PublicBookingLink
from app.domain.enums import BookingStatus
from app.domain.exceptions import (
    BookingLinkInvalidError,
    HoldExpiredError,
    InvalidCancellationTokenError,
    InvalidSlotSelectionError,
)
from app.domain.structs import BookableSlot, DailyAvailabilitySummary, TimeWindow
from app.domain.uow import AbstractUnitOfWork
from app.services.availability import AvailabilityDomainService


@dataclass(frozen=True, slots=True)
class WeeklyAvailabilityResult:
    advisor_display_name: str
    meeting_type: MeetingType
    slots: list[BookableSlot]


@dataclass(frozen=True, slots=True)
class MonthlyAvailabilityResult:
    advisor_display_name: str
    meeting_type: MeetingType
    days: list[DailyAvailabilitySummary]


@dataclass(frozen=True, slots=True)
class ConfirmedBookingResult:
    booking: Booking
    cancel_token: (
        str  # raw token returned ONCE to the user/email; only its SHA-256 hash is in DB
    )


def hash_cancel_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


class PublicBookingService:
    """
    Coordinates the public booking workflows across Domain Entities,
    AvailabilityDomainService, and the Unit of Work.
    """

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    async def _resolve_link_and_lock_tenant(
        self,
        uow: AbstractUnitOfWork,
        public_token: str,
        now: datetime,
    ) -> tuple[PublicBookingLink, MeetingType, str]:
        """
        Public requests arrive with only a public_token string, not an organization_id.
        1. temporarily enable bypass_rls=True to look up public_token.
        2. once found, lock pgsql RLS to link.organization_id with bypass_rls=False so all subsequent queries/writes
           in this transaction are fenced to that single tenant.
        """
        await uow.set_tenant_context(None, bypass_rls=True)
        resolved = await uow.schedules.get_active_booking_link(public_token, now)
        if resolved is None:
            raise BookingLinkInvalidError(
                "Booking link is invalid, inactive, or expired."
            )

        link, meeting_type, advisor_name = resolved
        link.validate_usable(now)

        await uow.set_tenant_context(link.organization_id, bypass_rls=False)
        return link, meeting_type, advisor_name

    async def get_weekly_availability(
        self,
        *,
        public_token: str,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> WeeklyAvailabilityResult:
        """
        Fetches bookable slots for 1-14 day window.
        Strips all internal meeting PII by querying only opaque busy TimeWindows.
        """
        if end_date < start_date or (end_date - start_date).days > 14:
            raise InvalidSlotSelectionError(
                "Weekly availability range must be between 1 and 14 days."
            )

        async with self._uow as uow:
            link, meeting_type, advisor_name = await self._resolve_link_and_lock_tenant(
                uow, public_token, now
            )

            # Pad fetch window by +- 1 day so timezone offsets and midnight buffers never clip a busy block
            padded_start = start_date - timedelta(days=1)
            padded_end = end_date + timedelta(days=1)
            search_window = TimeWindow(
                datetime.combine(padded_start, time.min, tzinfo=UTC),
                datetime.combine(padded_end, time.max, tzinfo=UTC),
            )

            rules = await uow.schedules.get_advisor_rules(
                link.organization_id, meeting_type.advisor_membership_id
            )
            overrides = await uow.schedules.get_advisor_overrides(
                link.organization_id,
                meeting_type.advisor_membership_id,
                padded_start,
                padded_end,
            )
            busy_windows = await uow.schedules.get_opaque_busy_windows(
                link.organization_id,
                meeting_type.advisor_membership_id,
                search_window,
                now,
            )

            slots = AvailabilityDomainService.compute_available_slots(
                rules=rules,
                overrides=overrides,
                busy_windows=busy_windows,
                meeting_type=meeting_type,
                start_date=start_date,
                end_date=end_date,
                now=now,
            )
            return WeeklyAvailabilityResult(
                advisor_display_name=advisor_name,
                meeting_type=meeting_type,
                slots=slots,
            )

    async def get_monthly_availability(
        self,
        *,
        public_token: str,
        year: int,
        month: int,
        viewer_timezone: str,
        now: datetime,
    ) -> MonthlyAvailabilityResult:
        """
        Computes daily slot counts and earliest start times for every day of (year, month)
        bucketed in the prospect's viewer_timezone.
        """
        if not (1 <= month <= 12):
            raise InvalidSlotSelectionError("Month must be between 1 and 12.")

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        padded_start = first_day - timedelta(days=2)
        padded_end = last_day + timedelta(days=2)

        async with self._uow as uow:
            link, meeting_type, advisor_name = await self._resolve_link_and_lock_tenant(
                uow, public_token, now
            )

            search_window = TimeWindow(
                datetime.combine(padded_start, time.min, tzinfo=UTC),
                datetime.combine(padded_end, time.max, tzinfo=UTC),
            )
            rules = await uow.schedules.get_advisor_rules(
                link.organization_id, meeting_type.advisor_membership_id
            )
            overrides = await uow.schedules.get_advisor_overrides(
                link.organization_id,
                meeting_type.advisor_membership_id,
                padded_start,
                padded_end,
            )
            busy_windows = await uow.schedules.get_opaque_busy_windows(
                link.organization_id,
                meeting_type.advisor_membership_id,
                search_window,
                now,
            )

            days = AvailabilityDomainService.compute_monthly_summary(
                rules=rules,
                overrides=overrides,
                busy_windows=busy_windows,
                meeting_type=meeting_type,
                year=year,
                month=month,
                viewer_timezone=viewer_timezone,
                now=now,
            )
            return MonthlyAvailabilityResult(
                advisor_display_name=advisor_name,
                meeting_type=meeting_type,
                days=days,
            )

    async def acquire_slot_hold(
        self,
        *,
        public_token: str,
        slot_window: TimeWindow,
        prospect_timezone: str,
        idempotency_key: str,
        now: datetime,
    ) -> Booking:
        """
        1. Resolve link & lock tenant RLS.
        2. Check idempotency_key first so network retries return the existing hold instead of 409 Conflict.
        3. Verify slot_window is actually inside the advisor's open working hours (since DB GiST
           only checks collisions with other bookings/meetings, not weekly business hours).
        4. Insert the HELD booking into pg, where excl_bookings_no_advisor_overlap and
           trg_bookings_jit_evict_and_check_meetings atomically guard against race conditions.
        """
        async with self._uow as uow:
            link, meeting_type, _ = await self._resolve_link_and_lock_tenant(
                uow, public_token, now
            )

            # Idempotency check
            existing = await uow.bookings.get_by_idempotency_key(
                link.organization_id, idempotency_key
            )
            if existing is not None:
                return existing

            # Validate slot against notice/duration rules AND advisor working hours
            meeting_type.validate_requested_slot(slot_window, now)
            await self._verify_slot_within_working_hours(
                uow=uow,
                organization_id=link.organization_id,
                meeting_type=meeting_type,
                slot_window=slot_window,
                now=now,
                exclude_booking_id=None,
            )

            # Create hold entity and insert (DB GiST index enforces atomic lock)
            booking = Booking.create_hold(
                booking_link=link,
                meeting_type=meeting_type,
                slot_window=slot_window,
                prospect_timezone=prospect_timezone,
                idempotency_key=idempotency_key,
                now=now,
            )
            await uow.bookings.add(booking)
            await uow.commit()
            return booking

    async def confirm_booking(
        self,
        *,
        public_token: str,
        booking_id: UUID,
        email: str,
        full_name: str,
        phone: str | None = None,
        company_name: str | None = None,
        meeting_topic: str | None = None,
        prospect_notes: str | None = None,
        now: datetime,
    ) -> ConfirmedBookingResult:
        """
        Atomically transitions a HELD booking to CONFIRMED in a transaction:
        1. Locks the HELD row with FOR UPDATE so concurrent requests cannot double-confirm.
        2. Validates the hold has not expired (now < hold_expires_at).
        3. Upserts public_prospects and links/provisions a clients record (status='provisioning').
        4. Creates the advisor's internal meetings row and pre-meeting AI Agent tasks row.
        5. Generates a cryptographic cancel_token (storing only its SHA-256 hash on bookings).
        """
        async with self._uow as uow:
            link, meeting_type, advisor_name = await self._resolve_link_and_lock_tenant(
                uow, public_token, now
            )

            booking = await uow.bookings.get_by_id(
                link.organization_id,
                link.subscription_id,
                booking_id,
                for_update=True,
            )
            if booking is None or booking.booking_link_id != link.id:
                raise HoldExpiredError(
                    "Reservation hold not found for this booking link."
                )

            # Check hold expiration before creating side-effect rows (prospect/client/meeting)
            if booking.status != BookingStatus.HELD:
                raise HoldExpiredError(
                    f"Booking cannot be confirmed from status {booking.status}."
                )
            if booking.hold_expires_at is None or booking.hold_expires_at <= now:
                booking.status = BookingStatus.EXPIRED
                await uow.bookings.save(booking)
                await uow.commit()
                raise HoldExpiredError(
                    "The reservation hold has expired. Please select a new slot."
                )

            # Upsert prospect & provision/link client
            (
                prospect_id,
                client_id,
            ) = await uow.bookings.upsert_prospect_and_provision_client(
                organization_id=link.organization_id,
                subscription_id=link.subscription_id,
                advisor_membership_id=meeting_type.advisor_membership_id,
                email=email,
                full_name=full_name,
                phone=phone,
                company_name=company_name,
            )

            # Attach client & notes prior to creating internal meeting & AI agent task
            booking.client_id = client_id
            booking.meeting_topic = meeting_topic
            booking.prospect_notes = prospect_notes

            internal_meeting_id = await uow.bookings.create_internal_meeting(
                booking=booking,
                meeting_type=meeting_type,
                prospect_full_name=full_name,
                prospect_email=email,
            )

            raw_cancel_token = secrets.token_urlsafe(32)
            token_hash = hash_cancel_token(raw_cancel_token)

            booking.confirm(
                prospect_id=prospect_id,
                client_id=client_id,
                internal_meeting_id=internal_meeting_id,
                cancel_token_hash=token_hash,
                meeting_topic=meeting_topic,
                prospect_notes=prospect_notes,
                now=now,
            )
            await uow.bookings.save(booking)

            await uow.commit()
            return ConfirmedBookingResult(
                booking=booking, cancel_token=raw_cancel_token
            )

    async def reschedule_booking(
        self,
        *,
        public_token: str,
        raw_cancel_token: str,
        new_slot_window: TimeWindow,
        now: datetime,
    ) -> Booking:
        """
        Atomically moves a confirmed booking to new_slot_window:
        1. Resolves link & locks tenant RLS.
        2. Looks up the booking by sha256(raw_cancel_token) with FOR UPDATE.
        3. Verifies new_slot_window is within working hours (excluding booking.id so the
           old slot doesn't block a slight 15-minute shift).
        4. Updates both bookings (slot_range, reserved_range) and meetings (scheduled_range)
           in the same transaction—PostgreSQL's GiST constraint guarantees the new slot is free.
        """
        token_hash = hash_cancel_token(raw_cancel_token)

        async with self._uow as uow:
            link, meeting_type, _ = await self._resolve_link_and_lock_tenant(
                uow, public_token, now
            )

            booking = await uow.bookings.get_by_cancel_token_hash(
                token_hash, for_update=True
            )
            if booking is None or booking.organization_id != link.organization_id:
                raise InvalidCancellationTokenError(
                    "Invalid or unknown management token."
                )

            meeting_type.validate_requested_slot(new_slot_window, now)
            await self._verify_slot_within_working_hours(
                uow=uow,
                organization_id=link.organization_id,
                meeting_type=meeting_type,
                slot_window=new_slot_window,
                now=now,
                exclude_booking_id=booking.id,
            )

            booking.reschedule(
                new_slot_window=new_slot_window,
                meeting_type=meeting_type,
                now=now,
            )
            await uow.bookings.save(booking)

            if booking.internal_meeting_id is not None:
                await uow.bookings.update_internal_meeting_schedule(
                    organization_id=booking.organization_id,
                    subscription_id=booking.subscription_id,
                    internal_meeting_id=booking.internal_meeting_id,
                    new_slot=new_slot_window,
                )

            await uow.commit()
            return booking

    async def cancel_booking(
        self,
        *,
        raw_cancel_token: str,
        reason: str | None,
        now: datetime,
    ) -> Booking:
        """
        Validates the prospect's raw_cancel_token, marks the booking CANCELLED
        (which immediately removes it from PostgreSQL's partial GiST exclusion index
        WHERE status IN ('HELD', 'CONFIRMED')), cancels the advisor's internal meeting
        """
        token_hash = hash_cancel_token(raw_cancel_token)

        async with self._uow as uow:
            # Bootstrap RLS to locate the booking by its unique cancel_token_hash
            await uow.set_tenant_context(None, bypass_rls=True)
            booking = await uow.bookings.get_by_cancel_token_hash(
                token_hash, for_update=True
            )
            if booking is None:
                raise InvalidCancellationTokenError(
                    "Invalid or unknown cancellation token."
                )

            # Lock RLS to the booking's organization for all subsequent mutations
            await uow.set_tenant_context(booking.organization_id, bypass_rls=False)

            booking.cancel(reason=reason, now=now)
            await uow.bookings.save(booking)

            if booking.internal_meeting_id is not None:
                await uow.bookings.cancel_internal_meeting(
                    organization_id=booking.organization_id,
                    subscription_id=booking.subscription_id,
                    internal_meeting_id=booking.internal_meeting_id,
                )

            await uow.commit()
            return booking

    @staticmethod
    async def _verify_slot_within_working_hours(
        *,
        uow: AbstractUnitOfWork,
        organization_id: UUID,
        meeting_type: MeetingType,
        slot_window: TimeWindow,
        now: datetime,
        exclude_booking_id: UUID | None,
    ) -> None:
        """
        Ensures a requested slot falls on an actual bookable grid boundary inside the
        advisor's open working hours (and does not collide with known busy windows).
        """
        target_date = slot_window.start_at.date()
        padded_start = target_date - timedelta(days=1)
        padded_end = target_date + timedelta(days=1)

        search_window = TimeWindow(
            datetime.combine(padded_start, time.min, tzinfo=UTC),
            datetime.combine(padded_end, time.max, tzinfo=UTC),
        )
        rules = await uow.schedules.get_advisor_rules(
            organization_id, meeting_type.advisor_membership_id
        )
        overrides = await uow.schedules.get_advisor_overrides(
            organization_id,
            meeting_type.advisor_membership_id,
            padded_start,
            padded_end,
        )
        busy_windows = await uow.schedules.get_opaque_busy_windows(
            organization_id,
            meeting_type.advisor_membership_id,
            search_window,
            now,
            exclude_booking_id=exclude_booking_id,
        )

        available_slots = AvailabilityDomainService.compute_available_slots(
            rules=rules,
            overrides=overrides,
            busy_windows=busy_windows,
            meeting_type=meeting_type,
            start_date=padded_start,
            end_date=padded_end,
            now=now,
        )
        if not any(s.slot_window == slot_window for s in available_slots):
            raise InvalidSlotSelectionError(
                "Requested time slot is outside the advisor's available schedule or already taken."
            )
