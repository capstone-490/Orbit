# 50% or more Ai-generated code

"""
this file defines the repository interfaces used by the app
repositories handle reading and saving data from the database
keep database operations separate from business logic
actual database queries are implemented in other classes
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from uuid import UUID

from app.domain.entities import (
    AvailabilityOverride,
    AvailabilityRule,
    Booking,
    Client,
    MeetingType,
    PublicBookingLink,
)
from app.domain.structs import TimeWindow


class AbstractScheduleRepository(ABC):
    """Read-only repository for resolving booking links and advisor schedules."""

    @abstractmethod
    async def get_active_booking_link(
        self,
        public_token: str,
        now: datetime,
    ) -> tuple[PublicBookingLink, MeetingType, str] | None:
        """Returns PublicBookingLink, MeetingType, advisor_display_name based on token provided."""
        raise NotImplementedError

    @abstractmethod
    async def get_advisor_rules(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
    ) -> list[AvailabilityRule]:
        raise NotImplementedError

    @abstractmethod
    async def get_advisor_overrides(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[AvailabilityOverride]:
        raise NotImplementedError

    @abstractmethod
    async def get_opaque_busy_windows(
        self,
        organization_id: UUID,
        advisor_membership_id: UUID,
        search_window: TimeWindow,
        now: datetime,
        exclude_booking_id: UUID | None = None,
    ) -> list[TimeWindow]:
        """Fetch anonymous busy intervals from active bookings and meetings."""
        raise NotImplementedError


class AbstractBookingRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        booking_id: UUID,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_idempotency_key(
        self,
        organization_id: UUID,
        idempotency_key: str,
    ) -> Booking | None:
        """Prevents duplicate holds/bookings if user re-submits or their network retries."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_cancel_token_hash(
        self,
        cancel_token_hash: str,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        """Looks up a CONFIRMED booking using the hash of the cancellation token."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, booking: Booking) -> None:
        """
        Inserts a new Booking (HELD or CONFIRMED).
        Must raise SlotOverlapConflictError if PostgreSQL rejects the insert with SQLSTATE 23P01.
        """
        raise NotImplementedError

    @abstractmethod
    async def save(self, booking: Booking) -> None:
        """Persist state."""
        raise NotImplementedError

    @abstractmethod
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
        """Upserts the prospect in public_prospects and creates client entry as provisioning."""
        raise NotImplementedError

    @abstractmethod
    async def create_internal_meeting_and_agent_task(
        self,
        *,
        booking: Booking,
        meeting_type: MeetingType,
        prospect_full_name: str,
        prospect_email: str,
    ) -> UUID:
        """Creates the advisor's private meetings row and pre-meeting task."""
        raise NotImplementedError

    @abstractmethod
    async def update_internal_meeting_schedule(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
        new_slot: TimeWindow,
    ) -> None:
        """Updates meetings.scheduled_range and sets completion_status = rescheduled."""
        raise NotImplementedError

    @abstractmethod
    async def cancel_internal_meeting_and_tasks(
        self,
        *,
        organization_id: UUID,
        subscription_id: UUID,
        internal_meeting_id: UUID,
    ) -> None:
        """Sets meetings.status = cancelled, is_busy = false, and cancels pending agent tasks."""
        raise NotImplementedError


class AbstractClientRepository(ABC):
    """Repository contract for clients table CRUD operations."""

    @abstractmethod
    async def get_by_id(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        client_id: UUID,
        *,
        for_update: bool = False,
    ) -> Client | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_subscription(
        self,
        organization_id: UUID,
        subscription_id: UUID,
        *,
        advisor_membership_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Client]:
        """Lists active/provisioning clients in a subscription."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, client: Client) -> None:
        """
        Inserts a new Client.
        Raises DuplicateClientEmailError if uq_clients_subscription_email is violated (SQLSTATE 23505).
        """
        raise NotImplementedError

    @abstractmethod
    async def save(self, client: Client) -> None:
        """
        Updates an existing Client (including profile edits, onboarding_stage, or soft_delete).
        Raises DuplicateClientEmailError on email collision.
        """
        raise NotImplementedError
