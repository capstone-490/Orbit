from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.schemas.public_booking import (
    AcquireSlotHoldRequest,
    BookingStatusResponse,
    CancelBookingRequest,
    ConfirmBookingRequest,
    ConfirmedBookingResponse,
    DailyAvailabilitySummarySchema,
    MonthlyAvailabilityResponse,
    PublicBookableSlotSchema,
    PublicMeetingTypeSchema,
    RescheduleBookingRequest,
    SlotHoldResponse,
    WeeklyAvailabilityResponse,
)
from app.dependencies.uow import get_clock, get_public_booking_service
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
from app.domain.structs import TimeWindow
from app.services.public_booking import PublicBookingService

router = APIRouter(prefix="/public/booking-links", tags=["Public Client Booking"])

# =============================================================================
# Domain Exception -> HTTP Status Code Registration
# =============================================================================


def register_booking_exception_handlers(app: FastAPI) -> None:
    """Maps pure Domain Exceptions to standard REST HTTP status codes."""

    @app.exception_handler(BookingDomainError)
    async def handle_booking_domain_error(
        _request: Request, exc: BookingDomainError
    ) -> JSONResponse:
        if isinstance(exc, (BookingLinkInvalidError, InvalidCancellationTokenError)):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, SlotOverlapConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(exc, HoldExpiredError):
            status_code = status.HTTP_410_GONE
        elif isinstance(exc, (InvalidSlotSelectionError, InvalidTimeWindowError)):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(exc, ClientNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, DuplicateClientEmailError):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=status_code,
            content={
                "error_type": type(exc).__name__,
                "detail": str(exc),
            },
        )


# =============================================================================
# Public Endpoints
# =============================================================================


@router.get(
    "/{public_token}/availability/weekly",
    response_model=WeeklyAvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_weekly_availability(
    public_token: str,
    start_date: date = Query(
        ..., description="Start date of the weekly view (YYYY-MM-DD)"
    ),
    end_date: date = Query(..., description="End date of the weekly view (YYYY-MM-DD)"),
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> WeeklyAvailabilityResponse:
    result = await service.get_weekly_availability(
        public_token=public_token,
        start_date=start_date,
        end_date=end_date,
        now=now,
    )
    mt = result.meeting_type
    return WeeklyAvailabilityResponse(
        advisor_display_name=result.advisor_display_name,
        meeting_type=PublicMeetingTypeSchema(
            slug=mt.slug,
            title=mt.title,
            description=mt.description,
            duration_minutes=mt.duration_minutes,
            meeting_mode=mt.meeting_mode,
        ),
        slots=[
            PublicBookableSlotSchema(
                start_at=s.start_at,
                end_at=s.end_at,
                duration_minutes=s.duration_minutes,
            )
            for s in result.slots
        ],
    )


@router.get(
    "/{public_token}/availability/monthly",
    response_model=MonthlyAvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_monthly_availability(
    public_token: str,
    year: int = Query(..., ge=2025, le=2100),
    month: int = Query(..., ge=1, le=12),
    viewer_timezone: str = Query(default="UTC"),
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> MonthlyAvailabilityResponse:
    try:
        ZoneInfo(viewer_timezone)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise InvalidSlotSelectionError(
            f"Invalid viewer_timezone: '{viewer_timezone}'."
        ) from exc

    result = await service.get_monthly_availability(
        public_token=public_token,
        year=year,
        month=month,
        viewer_timezone=viewer_timezone,
        now=now,
    )
    mt = result.meeting_type
    return MonthlyAvailabilityResponse(
        advisor_display_name=result.advisor_display_name,
        meeting_type=PublicMeetingTypeSchema(
            slug=mt.slug,
            title=mt.title,
            description=mt.description,
            duration_minutes=mt.duration_minutes,
            meeting_mode=mt.meeting_mode,
        ),
        days=[
            DailyAvailabilitySummarySchema(
                calendar_date=d.calendar_date,
                total_available_slots=d.total_available_slots,
                earliest_slot_start=d.earliest_slot_start,
                slots=[
                    PublicBookableSlotSchema(
                        start_at=s.start_at,
                        end_at=s.end_at,
                        duration_minutes=s.duration_minutes,
                    )
                    for s in d.slots
                ],
            )
            for d in result.days
        ],
    )


@router.post(
    "/{public_token}/holds",
    response_model=SlotHoldResponse,
    status_code=status.HTTP_201_CREATED,
)
async def acquire_slot_hold(
    public_token: str,
    payload: AcquireSlotHoldRequest,
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> SlotHoldResponse:
    booking = await service.acquire_slot_hold(
        public_token=public_token,
        slot_window=TimeWindow(payload.start_at, payload.end_at),
        prospect_timezone=payload.prospect_timezone,
        idempotency_key=payload.idempotency_key,
        now=now,
    )
    assert booking.hold_expires_at is not None
    return SlotHoldResponse(
        booking_id=booking.id,
        status=booking.status,
        start_at=booking.slot_window.start_at,
        end_at=booking.slot_window.end_at,
        hold_expires_at=booking.hold_expires_at,
    )


@router.post(
    "/{public_token}/bookings/{booking_id}/confirm",
    response_model=ConfirmedBookingResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_booking(
    public_token: str,
    booking_id: UUID,
    payload: ConfirmBookingRequest,
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> ConfirmedBookingResponse:
    result = await service.confirm_booking(
        public_token=public_token,
        booking_id=booking_id,
        email=str(payload.email),
        full_name=payload.full_name,
        phone=payload.phone,
        company_name=payload.company_name,
        meeting_topic=payload.meeting_topic,
        prospect_notes=payload.prospect_notes,
        now=now,
    )
    b = result.booking
    return ConfirmedBookingResponse(
        booking_id=b.id,
        status=b.status,
        start_at=b.slot_window.start_at,
        end_at=b.slot_window.end_at,
        prospect_timezone=b.prospect_timezone,
        meeting_topic=b.meeting_topic,
        cancel_token=result.cancel_token,
    )


@router.post(
    "/{public_token}/reschedule",
    response_model=BookingStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def reschedule_booking(
    public_token: str,
    payload: RescheduleBookingRequest,
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> BookingStatusResponse:
    booking = await service.reschedule_booking(
        public_token=public_token,
        raw_cancel_token=payload.cancel_token,
        new_slot_window=TimeWindow(payload.new_start_at, payload.new_end_at),
        now=now,
    )
    return BookingStatusResponse(
        booking_id=booking.id,
        status=booking.status,
        start_at=booking.slot_window.start_at,
        end_at=booking.slot_window.end_at,
        cancelled_at=booking.cancelled_at,
    )


@router.post(
    "/cancel",
    response_model=BookingStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_booking(
    payload: CancelBookingRequest,
    service: PublicBookingService = Depends(get_public_booking_service),
    now: datetime = Depends(get_clock),
) -> BookingStatusResponse:
    booking = await service.cancel_booking(
        raw_cancel_token=payload.cancel_token,
        reason=payload.reason,
        now=now,
    )
    return BookingStatusResponse(
        booking_id=booking.id,
        status=booking.status,
        start_at=booking.slot_window.start_at,
        end_at=booking.slot_window.end_at,
        cancelled_at=booking.cancelled_at,
    )
