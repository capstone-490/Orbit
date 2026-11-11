# Below 50% AI-generated

from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.api.v2.schemas.base import (
    RequestSchema,
    ResponseSchema,
    TimeSlotInput,
    validate_iana_timezone,
    validate_north_american_phone,
)
from app.domain.enums import BookingStatus, MeetingMode

# read-only availability schemas auto-mapped via from_attributes=True


class PublicMeetingTypeSchema(ResponseSchema):
    slug: str
    title: str
    description: str | None
    duration_minutes: int
    meeting_mode: MeetingMode


class PublicBookableSlotSchema(ResponseSchema):
    start_at: datetime
    end_at: datetime
    duration_minutes: int


class DailyAvailabilitySummarySchema(ResponseSchema):
    calendar_date: date
    total_available_slots: int
    earliest_slot_start: datetime | None
    slots: list[PublicBookableSlotSchema]


class WeeklyAvailabilityResponse(ResponseSchema):
    advisor_display_name: str
    meeting_type: PublicMeetingTypeSchema
    slots: list[PublicBookableSlotSchema]


class MonthlyAvailabilityResponse(ResponseSchema):
    advisor_display_name: str
    meeting_type: PublicMeetingTypeSchema
    days: list[DailyAvailabilitySummarySchema]


class AcquireSlotHoldRequest(TimeSlotInput):
    prospect_timezone: str = Field(default="UTC", min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("prospect_timezone")
    @classmethod
    def check_tz(cls, v: str) -> str:
        return validate_iana_timezone(v)


class RescheduleBookingRequest(TimeSlotInput):
    cancel_token: str = Field(min_length=16, max_length=256)


class ConfirmBookingRequest(RequestSchema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    company_name: str | None = Field(default=None, max_length=200)
    meeting_topic: str | None = Field(default=None, max_length=250)
    prospect_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str | None) -> str | None:
        return validate_north_american_phone(v)


class CancelBookingRequest(RequestSchema):
    cancel_token: str = Field(min_length=16, max_length=256)
    reason: str | None = Field(default=None, max_length=500)


class BookingStatusResponse(ResponseSchema):
    booking_id: UUID
    status: BookingStatus
    start_at: datetime
    end_at: datetime
    cancelled_at: datetime | None = None


class SlotHoldResponse(BookingStatusResponse):
    hold_expires_at: datetime


class ConfirmedBookingResponse(BookingStatusResponse):
    prospect_timezone: str
    meeting_topic: str | None
    cancel_token: str
