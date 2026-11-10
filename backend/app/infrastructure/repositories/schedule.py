# 50% or more AI-generated code
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    AvailabilityOverride,
    AvailabilityRule,
    MeetingType,
    PublicBookingLink,
)
from app.domain.enums import MeetingMode
from app.domain.repositories import AbstractScheduleRepository
from app.domain.structs import BufferConfig, TimeWindow
from app.infrastructure.repositories.helpers import _from_pg_tstzrange, _to_pg_tstzrange


class SqlAlchemyScheduleRepository(AbstractScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_booking_link(
        self,
        public_token: str,
        now: datetime,
    ) -> tuple[PublicBookingLink, MeetingType, str] | None:
        stmt = text(
            """
            SELECT
                pbl.id AS link_id,
                pbl.organization_id,
                pbl.subscription_id,
                pbl.organizer_membership_id,
                pbl.advisor_membership_id,
                pbl.meeting_type_id,
                pbl.public_token,
                pbl.title AS link_title,
                pbl.is_active AS link_active,
                pbl.expires_at,
                pbl.hold_ttl_seconds,
                mt.slug,
                mt.title AS mt_title,
                mt.description AS mt_description,
                mt.duration_minutes,
                mt.slot_interval_minutes,
                mt.buffer_before_minutes,
                mt.buffer_after_minutes,
                mt.minimum_notice_minutes,
                mt.max_days_in_advance,
                mt.meeting_mode,
                mt.pre_meeting_agent_id,
                mt.is_active AS mt_active,
                COALESCE(ap.display_name, 'Financial Advisor') AS advisor_display_name
            FROM public_booking_links pbl
            JOIN organizations o
              ON o.id = pbl.organization_id
             AND o.status = 'active'
            JOIN subscriptions s
              ON s.organization_id = pbl.organization_id
             AND s.id = pbl.subscription_id
             AND s.status = 'active'
            JOIN memberships m
              ON m.organization_id = pbl.organization_id
             AND m.id = pbl.advisor_membership_id
             AND m.status = 'active'
            JOIN identities i
              ON i.id = m.identity_id
             AND i.status = 'active'
            JOIN advisor_profiles ap
              ON ap.organization_id = pbl.organization_id
             AND ap.membership_id = pbl.advisor_membership_id
             AND ap.booking_enabled = TRUE
            JOIN meeting_types mt
              ON mt.organization_id = pbl.organization_id
             AND mt.subscription_id = pbl.subscription_id
             AND mt.id = pbl.meeting_type_id
             AND mt.is_active = TRUE
            WHERE pbl.public_token = :public_token
              AND pbl.is_active = TRUE
              AND pbl.expires_at > :now
            """
        )
        row = (
            (
                await self._session.execute(
                    stmt,
                    {"public_token": public_token, "now": now},
                )
            )
            .mappings()
            .first()
        )

        if row is None:
            return None

        booking_link = PublicBookingLink(
            id=row["link_id"],
            organization_id=row["organization_id"],
            subscription_id=row["subscription_id"],
            organizer_membership_id=row["organizer_membership_id"],
            advisor_membership_id=row["advisor_membership_id"],
            meeting_type_id=row["meeting_type_id"],
            public_token=row["public_token"],
            title=row["link_title"],
            is_active=row["link_active"],
            expires_at=row["expires_at"],
            hold_ttl_seconds=row["hold_ttl_seconds"],
        )
        meeting_type = MeetingType(
            id=row["meeting_type_id"],
            organization_id=row["organization_id"],
            subscription_id=row["subscription_id"],
            advisor_membership_id=row["advisor_membership_id"],
            slug=row["slug"],
            title=row["mt_title"],
            description=row["mt_description"],
            duration_minutes=row["duration_minutes"],
            slot_interval_minutes=row["slot_interval_minutes"],
            buffers=BufferConfig(
                before_minutes=row["buffer_before_minutes"],
                after_minutes=row["buffer_after_minutes"],
            ),
            minimum_notice_minutes=row["minimum_notice_minutes"],
            max_days_in_advance=row["max_days_in_advance"],
            meeting_mode=MeetingMode(row["meeting_mode"]),
            pre_meeting_agent_id=row["pre_meeting_agent_id"],
            is_active=row["mt_active"],
        )
        return booking_link, meeting_type, str(row["advisor_display_name"])

    async def get_advisor_rules(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
    ) -> list[AvailabilityRule]:
        stmt = text(
            """
            SELECT id, organization_id, advisor_membership_id, day_of_week,
                   start_time, end_time, timezone, is_active, valid_from, valid_until
            FROM availability_rules
            WHERE organization_id = :org_id
              AND advisor_membership_id = :advisor_id
              AND is_active = TRUE
            ORDER BY day_of_week, start_time
            """
        )
        rows = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "advisor_id": advisor_membership_id,
                    },
                )
            )
            .mappings()
            .all()
        )

        return [
            AvailabilityRule(
                id=row["id"],
                organization_id=row["organization_id"],
                advisor_membership_id=row["advisor_membership_id"],
                day_of_week=row["day_of_week"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                timezone=row["timezone"],
                is_active=row["is_active"],
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
            )
            for row in rows
        ]

    async def get_advisor_overrides(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[AvailabilityOverride]:
        stmt = text(
            """
            SELECT id, organization_id, advisor_membership_id, override_date,
                   is_available, custom_window, reason
            FROM availability_overrides
            WHERE organization_id = :org_id
              AND advisor_membership_id = :advisor_id
              AND override_date BETWEEN :start_date AND :end_date
            """
        )
        rows = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "advisor_id": advisor_membership_id,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
            )
            .mappings()
            .all()
        )

        return [
            AvailabilityOverride(
                id=row["id"],
                organization_id=row["organization_id"],
                advisor_membership_id=row["advisor_membership_id"],
                override_date=row["override_date"],
                is_available=row["is_available"],
                custom_window=(
                    _from_pg_tstzrange(row["custom_window"])
                    if row["custom_window"] is not None
                    else None
                ),
                reason=row["reason"],
            )
            for row in rows
        ]

    async def get_opaque_busy_windows(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        search_window: TimeWindow,
        now: datetime,
        exclude_booking_id: UUID | None = None,
    ) -> list[TimeWindow]:
        """
        PRIVACY BOUNDARY: Selects ONLY reserved_range and scheduled_range timestamps.
        Private meeting titles, agendas, and client IDs are never touched.
        """
        stmt = text(
            """
            SELECT reserved_range AS busy_range
            FROM bookings
            WHERE organization_id = :org_id
              AND advisor_membership_id = :advisor_id
              AND reserved_range && :search_window
              AND (
                  status = 'CONFIRMED'
                  OR (status = 'HELD' AND hold_expires_at > :now)
              )
              AND (CAST(:exclude_id AS uuid) IS NULL OR id != CAST(:exclude_id AS uuid))
            UNION ALL
            SELECT scheduled_range AS busy_range
            FROM meetings
            WHERE organization_id = :org_id
              AND advisor_membership_id = :advisor_id
              AND status = 'active'
              AND is_busy = TRUE
              AND deleted_at IS NULL
              AND scheduled_range && :search_window
              AND (
                  CAST(:exclude_id AS uuid) IS NULL
                  OR id IS DISTINCT FROM (
                      SELECT internal_meeting_id FROM bookings
                      WHERE organization_id = :org_id AND id = CAST(:exclude_id AS uuid)
                  )
              )
            """
        ).bindparams(bindparam("search_window", type_=TSTZRANGE))

        rows = (
            (
                await self._session.execute(
                    stmt,
                    {
                        "org_id": organization_id,
                        "advisor_id": advisor_membership_id,
                        "search_window": _to_pg_tstzrange(search_window),
                        "now": now,
                        "exclude_id": exclude_booking_id,
                    },
                )
            )
            .mappings()
            .all()
        )

        return [
            _from_pg_tstzrange(row["busy_range"])
            for row in rows
            if row["busy_range"] is not None
        ]
