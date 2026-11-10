# No substantial Ai-generated code

"""
this file defines the unit of work interface
it groups repositories together and manages database transactions
commit changes atomically, rollback when something fails
"""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self
from uuid import UUID

from app.domain.repositories import (
    AbstractBookingRepository,
    AbstractClientRepository,
    AbstractScheduleRepository,
)


class AbstractUnitOfWork(ABC):
    """
    Coordinates repository access and transaction lifecycle.
    """

    schedules: AbstractScheduleRepository
    bookings: AbstractBookingRepository
    clients: AbstractClientRepository

    async def __aenter__(self) -> Self:
        """return this object when entering the async with block"""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """auto rollback on exceptions."""
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def set_tenant_context(
        self,
        organization_id: UUID | None,
        *,
        bypass_rls: bool = False,
    ) -> None:
        # set the current organization for database row-level security
        # bypass rls only when access outside normal tenant rules is needed
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError
