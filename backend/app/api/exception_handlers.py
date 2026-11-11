from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    BookingDomainError,
    BookingLinkInvalidError,
    ClientNotFoundError,
    DuplicateClientEmailError,
    HoldExpiredError,
    InvalidCancellationTokenError,
    InvalidSlotSelectionError,
    InvalidTimeWindowError,
    SlotOverlapConflictError,
)


def register_domain_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BookingDomainError)
    async def handle_domain_error(
        _request: Request, exc: BookingDomainError
    ) -> JSONResponse:
        if isinstance(
            exc,
            (
                BookingLinkInvalidError,
                InvalidCancellationTokenError,
                ClientNotFoundError,
            ),
        ):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, (SlotOverlapConflictError, DuplicateClientEmailError)):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(exc, HoldExpiredError):
            status_code = status.HTTP_410_GONE
        elif isinstance(exc, (InvalidSlotSelectionError, InvalidTimeWindowError)):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=status_code,
            content={
                "error_type": type(exc).__name__,
                "detail": str(exc),
            },
        )
