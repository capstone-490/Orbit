# No substantial AI-generated code
from datetime import UTC, datetime

from fastapi import Depends, Request

from app.domain.uow import AbstractUnitOfWork
from app.infrastructure.uow import SqlAlchemyUnitOfWork
from app.services.public_booking import PublicBookingService


def get_clock() -> datetime:
    """Returns current UTC time; overridable in tests to freeze or advance time."""
    return datetime.now(tz=UTC)


def get_uow(request: Request) -> AbstractUnitOfWork:
    """
    reads 'session_factory' initialized in app/lifecycle/lifespan.py and returns
    a request-scoped SqlAlchemyUnitOfWork.
    """
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError(
            "app.state.session_factory is not initialized. "
            "Ensure FastAPI lifespan is active or override 'get_uow' in tests."
        )
    return SqlAlchemyUnitOfWork(session_factory)


def get_public_booking_service(
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> PublicBookingService:
    """Injects the UnitOfWork into PublicBookingService for FastAPI routers."""
    return PublicBookingService(uow)
