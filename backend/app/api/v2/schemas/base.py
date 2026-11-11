from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, model_validator


class RequestSchema(BaseModel):
    """base for all ingress JSON request body: rejects unknown extra fields."""

    model_config = ConfigDict(extra="forbid")


class ResponseSchema(BaseModel):
    """
    base for all egress JSON responses:
    auto extract public params from entities
    and drops all unlisted private params.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)


class TimeSlotInput(RequestSchema):
    """base for requests that accept a [start, end)."""

    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> TimeSlotInput:
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at and end_at must include a timezone offset.")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be strictly after start_at.")
        return self


def validate_iana_timezone(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise ValueError(f"Invalid IANA timezone: '{tz_name}'.") from exc
    return tz_name


def validate_north_american_phone(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    phone = value.strip()
    if not re.fullmatch(r"\+?[\d\s().-]+", phone):
        raise ValueError("Please enter a valid Canadian phone number.")

    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    elif len(digits) != 10:
        raise ValueError("Please enter a valid 10-digit phone number.")

    if digits[0] not in "23456789" or digits[3] not in "23456789":
        raise ValueError("Please enter a valid Canadian phone number.")

    return phone
