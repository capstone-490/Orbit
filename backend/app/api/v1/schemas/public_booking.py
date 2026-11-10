from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.domain.enums import BookingStatus, MeetingMode


def _validate_iana_timezone(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise ValueError(f"Invalid IANA timezone: '{tz_name}'.") from exc
    return tz_name


class PublicMeetingTypeSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    description: str | None
    duration_minutes: int
    meeting_mode: MeetingMode


class PublicBookableSlotSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_at: datetime
    end_at: datetime
    duration_minutes: int


class DailyAvailabilitySummarySchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    calendar_date: date
    total_available_slots: int
    earliest_slot_start: datetime | None
    slots: list[PublicBookableSlotSchema]


class WeeklyAvailabilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    advisor_display_name: str
    meeting_type: PublicMeetingTypeSchema
    slots: list[PublicBookableSlotSchema]


class MonthlyAvailabilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    advisor_display_name: str
    meeting_type: PublicMeetingTypeSchema
    days: list[DailyAvailabilitySummarySchema]


class AcquireSlotHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: datetime
    end_at: datetime
    prospect_timezone: str = Field(default="UTC", min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("prospect_timezone")
    @classmethod
    def check_timezone(cls, v: str) -> str:
        return _validate_iana_timezone(v)

    @model_validator(mode="after")
    def check_time_order(self) -> AcquireSlotHoldRequest:
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError(
                "start_at and end_at must include a timezone offset (ISO-8601)."
            )
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be strictly after start_at.")
        return self


class SlotHoldResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    booking_id: UUID
    status: BookingStatus
    start_at: datetime
    end_at: datetime
    hold_expires_at: datetime


class ConfirmBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    company_name: str | None = Field(default=None, max_length=200)
    meeting_topic: str | None = Field(default=None, max_length=250)
    prospect_notes: str | None = Field(default=None, max_length=2000)


class ConfirmedBookingResponse(BaseModel):
    """
    Returns the confirmed appointment details and the one-time raw `cancel_token`
    (so the frontend can display a direct cancel/reschedule link on the confirmation page).
    Notice that internal `client_id` and `internal_meeting_id` are NEVER exposed here!
    """

    model_config = ConfigDict(frozen=True)

    booking_id: UUID
    status: BookingStatus
    start_at: datetime
    end_at: datetime
    prospect_timezone: str
    meeting_topic: str | None
    cancel_token: str


class RescheduleBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancel_token: str = Field(min_length=16, max_length=256)
    new_start_at: datetime
    new_end_at: datetime

    @model_validator(mode="after")
    def check_time_order(self) -> RescheduleBookingRequest:
        if self.new_start_at.tzinfo is None or self.new_end_at.tzinfo is None:
            raise ValueError(
                "new_start_at and new_end_at must include a timezone offset."
            )
        if self.new_end_at <= self.new_start_at:
            raise ValueError("new_end_at must be strictly after new_start_at.")
        return self


class CancelBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancel_token: str = Field(min_length=16, max_length=256)
    reason: str | None = Field(default=None, max_length=500)


class BookingStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    booking_id: UUID
    status: BookingStatus
    start_at: datetime
    end_at: datetime
    cancelled_at: datetime | None = None
