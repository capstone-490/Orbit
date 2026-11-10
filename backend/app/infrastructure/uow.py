# No Substantial Ai-generated code
from __future__ import annotations

from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.uow import AbstractUnitOfWork
from app.infrastructure.repositories.booking import SqlAlchemyBookingRepository
from app.infrastructure.repositories.client import SqlAlchemyClientRepository
from app.infrastructure.repositories.schedule import SqlAlchemyScheduleRepository


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    Used to share a session among multiple repositories and control lifecycle of a transaction for multiple queries in sequence.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Prepares session. factory knows how to create db sessions, and we store it.
        """

        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        """
        Open a session and provides workers access to this session.
        """
        if self._session is not None:
            raise RuntimeError("UnitOfWork is already active.")

        self._session = self._session_factory()
        self.schedules = SqlAlchemyScheduleRepository(self._session)
        self.bookings = SqlAlchemyBookingRepository(self._session)
        self.clients = SqlAlchemyClientRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            # ask parent to save work or rollback
            await super().__aexit__(exc_type, exc_val, exc_tb)
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def set_tenant_context(
        self,
        organization_id: UUID | None,
        *,
        bypass_rls: bool = False,
    ) -> None:
        """
        Sets transaction psql session (is_local = true)
        used by RLS functions current_tenant_org_id() and is_rls_bypassed().
        """
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not active.")

        # tell db which orgs info we are allowed to see
        # only lasts for the duration of this transaction
        await self._session.execute(
            text(
                """
                SELECT
                    set_config('app.current_org_id', :org_id, true),
                    set_config('app.bypass_rls', :bypass, true)
                """
            ),
            {
                "org_id": str(organization_id) if organization_id is not None else "",
                "bypass": "on" if bypass_rls else "off",
            },
        )

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not active.")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not active.")
        await self._session.rollback()
