# Below 50% AI-generated code

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v2.schemas.base import validate_iana_timezone
from app.api.v2.schemas.public_booking import (
    AcquireSlotHoldRequest,
    BookingStatusResponse,
    CancelBookingRequest,
    ConfirmBookingRequest,
    ConfirmedBookingResponse,
    MonthlyAvailabilityResponse,
    RescheduleBookingRequest,
    SlotHoldResponse,
    WeeklyAvailabilityResponse,
)
from app.dependencies.uow import get_clock, get_public_booking_service
from app.domain.exceptions import InvalidSlotSelectionError
from app.domain.structs import TimeWindow
from app.services.public_booking import PublicBookingService

router = APIRouter(prefix="/public/booking-links", tags=["Public Client Booking"])


@router.get(
    "/{public_token}/availability/weekly",
    response_model=WeeklyAvailabilityResponse,
)
async def get_weekly_availability(
    public_token: str,
    start_date: Annotated[
        date,
        Query(description="Start date of the weekly view (YYYY-MM-DD)"),
    ],
    end_date: Annotated[
        date,
        Query(description="End date of the weekly view (YYYY-MM-DD)"),
    ],
    service: Annotated[
        PublicBookingService,
        Depends(get_public_booking_service),
    ],
    now: Annotated[datetime, Depends(get_clock)],
) -> WeeklyAvailabilityResponse:
    result = await service.get_weekly_availability(
        public_token=public_token,
        start_date=start_date,
        end_date=end_date,
        now=now,
    )
    return WeeklyAvailabilityResponse.model_validate(result)


@router.get(
    "/{public_token}/availability/monthly",
    response_model=MonthlyAvailabilityResponse,
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
        validate_iana_timezone(viewer_timezone)
    except ValueError as exc:
        raise InvalidSlotSelectionError(str(exc)) from exc

    result = await service.get_monthly_availability(
        public_token=public_token,
        year=year,
        month=month,
        viewer_timezone=viewer_timezone,
        now=now,
    )
    return MonthlyAvailabilityResponse.model_validate(result)


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
    return SlotHoldResponse.model_validate(booking)


@router.post(
    "/{public_token}/bookings/{booking_id}/confirm",
    response_model=ConfirmedBookingResponse,
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
    return ConfirmedBookingResponse.model_validate(result)


@router.post(
    "/{public_token}/reschedule",
    response_model=BookingStatusResponse,
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
        new_slot_window=TimeWindow(payload.start_at, payload.end_at),
        now=now,
    )
    return BookingStatusResponse.model_validate(booking)


@router.post(
    "/cancel",
    response_model=BookingStatusResponse,
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
    return BookingStatusResponse.model_validate(booking)
