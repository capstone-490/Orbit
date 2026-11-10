# 50% or more AI-generated code

# this file contains the sqlachemy repository implementations
# repositories handle communication between the app and postgres
# convert database results into domain entities before returning them
# keep sql queries and database specific logic out of domain classes

from __future__ import annotations

from uuid import UUID, uuid7

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Booking, MeetingType
from app.domain.enums import BookingStatus
from app.domain.exceptions import HoldExpiredError, SlotOverlapConflictError
from app.domain.repositories import AbstractBookingRepository
from app.domain.structs import TimeWindow
from app.infrastructure.repositories.helpers import (
    _from_pg_tstzrange,
    _is_exclusion_violation,
    _to_pg_tstzrange,
)


class SqlAlchemyBookingRepository(AbstractBookingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        booking_id: UUID,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        lock_clause = "FOR UPDATE" if for_update else ""
        stmt = text(
            f"""
            SELECT id, organization_id, subscription_id, advisor_membership_id,
                   booking_link_id, meeting_type_id, prospect_id, client_id,
                   internal_meeting_id, status, slot_range, reserved_range,
                   prospect_timezone, meeting_topic, prospect_notes,
                   hold_expires_at, cancel_token_hash, cancelled_at,
                   cancellation_reason, rescheduled_from_id, idempotency_key, version
            FROM bookings
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND id = :booking_id
            {lock_clause}
            """
        )
        row = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "sub_id": subscription_id,
                        "booking_id": booking_id,
                    },
                )
            )
            .mappings()
            .first()
        )

        return self._row_to_entity(dict(row)) if row else None

    # find an existing request before creating another booking
    # prevent duplicate bookings when network requests are repeated
    async def get_by_idempotency_key(
        self,
        organization_id: UUID,
        idempotency_key: str,
    ) -> Booking | None:
        stmt = text(
            """
            SELECT id, organization_id, subscription_id, advisor_membership_id,
                   booking_link_id, meeting_type_id, prospect_id, client_id,
                   internal_meeting_id, status, slot_range, reserved_range,
                   prospect_timezone, meeting_topic, prospect_notes,
                   hold_expires_at, cancel_token_hash, cancelled_at,
                   cancellation_reason, rescheduled_from_id, idempotency_key, version
            FROM bookings
            WHERE organization_id = :org_id
              AND idempotency_key = :idempotency_key
            """
        )
        row = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "idempotency_key": idempotency_key,
                    },
                )
            )
            .mappings()
            .first()
        )

        return self._row_to_entity(dict(row)) if row else None

    async def get_by_cancel_token_hash(
        self,
        cancel_token_hash: str,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        lock_clause = "FOR UPDATE" if for_update else ""
        stmt = text(
            f"""
            SELECT id, organization_id, subscription_id, advisor_membership_id,
                   booking_link_id, meeting_type_id, prospect_id, client_id,
                   internal_meeting_id, status, slot_range, reserved_range,
                   prospect_timezone, meeting_topic, prospect_notes,
                   hold_expires_at, cancel_token_hash, cancelled_at,
                   cancellation_reason, rescheduled_from_id, idempotency_key, version
            FROM bookings
            WHERE cancel_token_hash = :cancel_token_hash
            {lock_clause}
            """
        )
        row = (
            (
                await self._session.execute(
                    stmt,
                    {"cancel_token_hash": cancel_token_hash},
                )
            )
            .mappings()
            .first()
        )

        return self._row_to_entity(dict(row)) if row else None

    async def add(self, booking: Booking) -> None:
        """
        Inserts a booking row.
        pgsql's trg_bookings_jit_evict_and_check_meetings trigger automatically:
          1. Acquires the advisor schedule advisory lock (lock_advisor_schedule_keys).
          2. Evicts any overlapping expired holds (status = 'HELD' AND hold_expires_at <= now()).
          3. Rejects overlaps with busy meetings (raising SQLSTATE 23P01).
        And excl_bookings_no_advisor_overlap rejects overlaps with active bookings (raising SQLSTATE 23P01).
        """

        conflict_stmt = text(
            """
            SELECT 1 FROM meetings
            WHERE organization_id = :org_id
              AND advisor_membership_id = :advisor_id
              AND status = 'active'
              AND is_busy = TRUE
              AND deleted_at IS NULL
              AND scheduled_range && :reserved_range
            LIMIT 1
            """
        ).bindparams(
            bindparam("reserved_range", type_=TSTZRANGE),
        )
        conflict = (
            await self._session.execute(
                conflict_stmt,
                {
                    "org_id": booking.organization_id,
                    "advisor_id": booking.advisor_membership_id,
                    "reserved_range": _to_pg_tstzrange(booking.reserved_window),
                },
            )
        ).first()
        if conflict is not None:
            raise SlotOverlapConflictError(
                "Requested slot overlaps with an internal advisor meeting."
            )

        stmt = text(
            """
            INSERT INTO bookings (
                id, organization_id, subscription_id, advisor_membership_id,
                booking_link_id, meeting_type_id, prospect_id, client_id,
                internal_meeting_id, status, slot_range, reserved_range,
                prospect_timezone, meeting_topic, prospect_notes,
                hold_expires_at, cancel_token_hash, cancelled_at,
                cancellation_reason, rescheduled_from_id, idempotency_key, version
            ) VALUES (
                :id, :org_id, :sub_id, :advisor_id,
                :link_id, :mt_id, :prospect_id, :client_id,
                :internal_meeting_id, :status, :slot_range, :reserved_range,
                :prospect_tz, :topic, :notes,
                :hold_expires_at, :cancel_token_hash, :cancelled_at,
                :cancellation_reason, :rescheduled_from_id, :idempotency_key, :version
            )
            """
        ).bindparams(
            bindparam("slot_range", type_=TSTZRANGE),
            bindparam("reserved_range", type_=TSTZRANGE),
        )

        try:
            await self._session.execute(
                stmt,
                {
                    "id": booking.id,
                    "org_id": booking.organization_id,
                    "sub_id": booking.subscription_id,
                    "advisor_id": booking.advisor_membership_id,
                    "link_id": booking.booking_link_id,
                    "mt_id": booking.meeting_type_id,
                    "prospect_id": booking.prospect_id,
                    "client_id": booking.client_id,
                    "internal_meeting_id": booking.internal_meeting_id,
                    "status": booking.status.value,
                    "slot_range": _to_pg_tstzrange(booking.slot_window),
                    "reserved_range": _to_pg_tstzrange(booking.reserved_window),
                    "prospect_tz": booking.prospect_timezone,
                    "topic": booking.meeting_topic,
                    "notes": booking.prospect_notes,
                    "hold_expires_at": booking.hold_expires_at,
                    "cancel_token_hash": booking.cancel_token_hash,
                    "cancelled_at": booking.cancelled_at,
                    "cancellation_reason": booking.cancellation_reason,
                    "rescheduled_from_id": booking.rescheduled_from_id,
                    "idempotency_key": booking.idempotency_key,
                    "version": booking.version,
                },
            )
        except DBAPIError as exc:
            if _is_exclusion_violation(exc):
                raise SlotOverlapConflictError(
                    "The selected time slot conflicts with an existing booking or advisor meeting."
                ) from exc
            raise

    # update the booking record with its latest values
    # also sync internal meeting if topic or notes changed
    async def save(self, booking: Booking) -> None:
        stmt = text(
            """
            UPDATE bookings
            SET prospect_id = :prospect_id,
                client_id = :client_id,
                internal_meeting_id = :internal_meeting_id,
                status = :status,
                slot_range = :slot_range,
                reserved_range = :reserved_range,
                meeting_topic = :topic,
                prospect_notes = :notes,
                hold_expires_at = :hold_expires_at,
                cancel_token_hash = :cancel_token_hash,
                cancelled_at = :cancelled_at,
                cancellation_reason = :cancellation_reason,
                version = :version
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND id = :id
            """
        ).bindparams(
            bindparam("slot_range", type_=TSTZRANGE),
            bindparam("reserved_range", type_=TSTZRANGE),
        )

        try:
            await self._session.execute(
                stmt,
                {
                    "id": booking.id,
                    "org_id": booking.organization_id,
                    "sub_id": booking.subscription_id,
                    "prospect_id": booking.prospect_id,
                    "client_id": booking.client_id,
                    "internal_meeting_id": booking.internal_meeting_id,
                    "status": booking.status.value,
                    "slot_range": _to_pg_tstzrange(booking.slot_window),
                    "reserved_range": _to_pg_tstzrange(booking.reserved_window),
                    "topic": booking.meeting_topic,
                    "notes": booking.prospect_notes,
                    "hold_expires_at": booking.hold_expires_at,
                    "cancel_token_hash": booking.cancel_token_hash,
                    "cancelled_at": booking.cancelled_at,
                    "cancellation_reason": booking.cancellation_reason,
                    "version": booking.version,
                },
            )
            # If create_internal_meeting_and_agent_task was invoked prior to booking.confirm(),
            # synchronize the linked internal meeting's agenda and pre-meeting task description.
            if booking.internal_meeting_id is not None and (
                booking.meeting_topic or booking.prospect_notes
            ):
                await self._session.execute(
                    text(
                        """
                        UPDATE meetings
                        SET agenda = COALESCE(agenda, :agenda)
                        WHERE organization_id = :org_id
                          AND subscription_id = :sub_id
                          AND id = :meeting_id
                        """
                    ),
                    {
                        "agenda": booking.meeting_topic or booking.prospect_notes,
                        "org_id": booking.organization_id,
                        "sub_id": booking.subscription_id,
                        "meeting_id": booking.internal_meeting_id,
                    },
                )
                if booking.meeting_topic:
                    await self._session.execute(
                        text(
                            """
                            UPDATE tasks
                            SET description = replace(
                                description,
                                'Topic: General Consultation.',
                                :topic_suffix
                            )
                            WHERE organization_id = :org_id
                              AND subscription_id = :sub_id
                              AND meeting_id = :meeting_id
                              AND description LIKE '%Topic: General Consultation.%'
                            """
                        ),
                        {
                            "topic_suffix": f"Topic: {booking.meeting_topic}.",
                            "org_id": booking.organization_id,
                            "sub_id": booking.subscription_id,
                            "meeting_id": booking.internal_meeting_id,
                        },
                    )
        except DBAPIError as exc:
            if _is_exclusion_violation(exc):
                raise SlotOverlapConflictError(
                    "The updated time slot conflicts with an existing booking or advisor meeting."
                ) from exc
            raise

    # normalize email and name before saving
    # use upsert so repeated requests update existing prospect
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
    ) -> tuple[UUID, UUID | None]:
        normalized_email = email.strip().lower()
        normalized_name = full_name.strip()

        upsert_prospect_stmt = text(
            """
            INSERT INTO public_prospects (
                id, organization_id, subscription_id, email, full_name, phone, company_name
            ) VALUES (
                :id, :org_id, :sub_id, :email, :full_name, :phone, :company_name
            )
            ON CONFLICT (organization_id, subscription_id, lower(email))
            DO UPDATE SET
                full_name = EXCLUDED.full_name,
                phone = COALESCE(EXCLUDED.phone, public_prospects.phone),
                company_name = COALESCE(EXCLUDED.company_name, public_prospects.company_name)
            RETURNING id, linked_client_id
            """
        )
        prospect_row = (
            (
                await self._session.execute(
                    upsert_prospect_stmt,
                    {
                        "id": uuid7(),
                        "org_id": organization_id,
                        "sub_id": subscription_id,
                        "email": normalized_email,
                        "full_name": normalized_name,
                        "phone": phone,
                        "company_name": company_name,
                    },
                )
            )
            .mappings()
            .one()
        )

        prospect_id: UUID = prospect_row["id"]
        client_id: UUID | None = prospect_row["linked_client_id"]

        if client_id is None:
            upsert_client_stmt = text(
                """
                INSERT INTO clients (
                    id, organization_id, subscription_id, display_name,
                    email, phone, primary_advisor_membership_id, status
                ) VALUES (
                    :client_id, :org_id, :sub_id, :display_name,
                    :email, :phone, :advisor_id, 'provisioning'
                )
                ON CONFLICT (organization_id, subscription_id, lower(email))
                WHERE deleted_at IS NULL AND email IS NOT NULL
                DO UPDATE SET
                    phone = COALESCE(clients.phone, EXCLUDED.phone)
                RETURNING id
                """
            )
            client_id = (
                await self._session.execute(
                    upsert_client_stmt,
                    {
                        "client_id": uuid7(),
                        "org_id": organization_id,
                        "sub_id": subscription_id,
                        "display_name": normalized_name,
                        "email": normalized_email,
                        "phone": phone,
                        "advisor_id": advisor_membership_id,
                    },
                )
            ).scalar_one()

            await self._session.execute(
                text(
                    """
                    UPDATE public_prospects
                    SET linked_client_id = :client_id
                    WHERE organization_id = :org_id
                      AND subscription_id = :sub_id
                      AND id = :prospect_id
                    """
                ),
                {
                    "client_id": client_id,
                    "org_id": organization_id,
                    "sub_id": subscription_id,
                    "prospect_id": prospect_id,
                },
            )

        return prospect_id, client_id

    async def create_internal_meeting(
        self,
        *,
        booking: Booking,
        meeting_type: MeetingType,
        prospect_full_name: str,
        prospect_email: str,
    ) -> UUID:
        """
        Creates the internal meetings row (note: scheduled_at and duration_minutes are
        GENERATED ALWAYS columns in schema, so only insert scheduled_range!)
        and creates the pre-meeting dossier tasks row.
        """
        meeting_id = uuid7()
        insert_meeting_stmt = text(
            """
            INSERT INTO meetings (
                id, organization_id, subscription_id, advisor_membership_id,
                meeting_type_id, client_id, title, agenda, meeting_mode,
                is_busy, organizer_membership_id, scheduled_range,
                status, completion_status
            ) VALUES (
                :id, :org_id, :sub_id, :advisor_id,
                :mt_id, :client_id, :title, :agenda, :meeting_mode,
                TRUE, :advisor_id, :scheduled_range,
                'provisioning', 'scheduled'
            )
            """
        ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE))

        try:
            await self._session.execute(
                insert_meeting_stmt,
                {
                    "id": meeting_id,
                    "org_id": booking.organization_id,
                    "sub_id": booking.subscription_id,
                    "advisor_id": booking.advisor_membership_id,
                    "mt_id": meeting_type.id,
                    "client_id": booking.client_id,
                    "title": f"{meeting_type.title} — {prospect_full_name}",
                    "agenda": booking.meeting_topic or booking.prospect_notes,
                    "meeting_mode": meeting_type.meeting_mode.value,
                    "scheduled_range": _to_pg_tstzrange(booking.slot_window),
                },
            )

            link_booking_result = await self._session.execute(
                text(
                    """
                    UPDATE bookings
                    SET internal_meeting_id = :meeting_id
                    WHERE organization_id = :org_id
                      AND subscription_id = :sub_id
                      AND id = :booking_id
                      AND status = 'HELD'
                      AND hold_expires_at > now()
                    RETURNING id
                    """
                ),
                {
                    "meeting_id": meeting_id,
                    "org_id": booking.organization_id,
                    "sub_id": booking.subscription_id,
                    "booking_id": booking.id,
                },
            )
            linked_booking_id = link_booking_result.scalar_one_or_none()

            # link meeting to booking only if the hold is valid
            if linked_booking_id is None:
                raise HoldExpiredError(
                    "Could not associate internal meeting with booking: hold is missing or expired."
                )

            booking.internal_meeting_id = meeting_id

            await self._session.execute(
                text(
                    """
                    UPDATE meetings
                    SET status = 'active'
                    WHERE organization_id = :org_id
                      AND subscription_id = :sub_id
                      AND id = :meeting_id
                    """
                ),
                {
                    "org_id": booking.organization_id,
                    "sub_id": booking.subscription_id,
                    "meeting_id": meeting_id,
                },
            )
        except DBAPIError as exc:
            if _is_exclusion_violation(exc):
                raise SlotOverlapConflictError(
                    "Advisor already has an overlapping internal meeting."
                ) from exc
            raise

        return meeting_id

    async def update_internal_meeting_schedule(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
        new_slot: TimeWindow,
    ) -> None:
        stmt = text(
            """
            UPDATE meetings
            SET scheduled_range = :scheduled_range,
                completion_status = 'rescheduled'
            WHERE organization_id = :org_id
              AND subscription_id = :sub_id
              AND id = :meeting_id
            """
        ).bindparams(bindparam("scheduled_range", type_=TSTZRANGE))

        try:
            await self._session.execute(
                stmt,
                {
                    "org_id": organization_id,
                    "sub_id": subscription_id,
                    "meeting_id": internal_meeting_id,
                    "scheduled_range": _to_pg_tstzrange(new_slot),
                },
            )
        except DBAPIError as exc:
            if _is_exclusion_violation(exc):
                raise SlotOverlapConflictError(
                    "Rescheduled slot overlaps with an existing internal meeting."
                ) from exc
            raise

    async def cancel_internal_meeting(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE meetings
                SET status = 'cancelled', is_busy = FALSE
                WHERE organization_id = :org_id
                  AND subscription_id = :sub_id
                  AND id = :meeting_id
                """
            ),
            {
                "org_id": organization_id,
                "sub_id": subscription_id,
                "meeting_id": internal_meeting_id,
            },
        )

    @staticmethod
    def _row_to_entity(row: dict[str, object]) -> Booking:
        return Booking(
            id=row["id"],  # type: ignore[arg-type]
            organization_id=row["organization_id"],  # type: ignore[arg-type]
            subscription_id=row["subscription_id"],  # type: ignore[arg-type]
            advisor_membership_id=row["advisor_membership_id"],  # type: ignore[arg-type]
            booking_link_id=row["booking_link_id"],  # type: ignore[arg-type]
            meeting_type_id=row["meeting_type_id"],  # type: ignore[arg-type]
            prospect_id=row["prospect_id"],  # type: ignore[arg-type]
            client_id=row["client_id"],  # type: ignore[arg-type]
            internal_meeting_id=row["internal_meeting_id"],  # type: ignore[arg-type]
            status=BookingStatus(str(row["status"])),
            slot_window=_from_pg_tstzrange(row["slot_range"]),  # type: ignore[arg-type]
            reserved_window=_from_pg_tstzrange(row["reserved_range"]),  # type: ignore[arg-type]
            prospect_timezone=str(row["prospect_timezone"]),
            meeting_topic=row["meeting_topic"],  # type: ignore[arg-type]
            prospect_notes=row["prospect_notes"],  # type: ignore[arg-type]
            hold_expires_at=row["hold_expires_at"],  # type: ignore[arg-type]
            cancel_token_hash=row["cancel_token_hash"],  # type: ignore[arg-type]
            cancelled_at=row["cancelled_at"],  # type: ignore[arg-type]
            cancellation_reason=row["cancellation_reason"],  # type: ignore[arg-type]
            rescheduled_from_id=row["rescheduled_from_id"],  # type: ignore[arg-type]
            idempotency_key=str(row["idempotency_key"]),
            version=int(row["version"]),  # type: ignore[arg-type]
        )
