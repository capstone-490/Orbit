# Below 50% AI-generated
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.api.v2.schemas.base import (
    RequestSchema,
    ResponseSchema,
    validate_north_american_phone,
)
from app.domain.enums import ClientStatus, OnboardingStage


class _ClientMutableFields(RequestSchema):
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    occupation: str | None = None
    onboarding_stage: OnboardingStage | None = None

    @field_validator("address", "occupation", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str | None) -> str | None:
        return validate_north_american_phone(v)


class ClientCreateRequest(_ClientMutableFields):
    display_name: str = Field(min_length=1, max_length=200)


class ClientUpdateRequest(_ClientMutableFields):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    status: ClientStatus | None = None


class ClientResponse(ResponseSchema):
    id: UUID
    organization_id: UUID
    subscription_id: UUID
    display_name: str
    email: str | None
    phone: str | None
    address: str | None
    date_of_birth: date | None
    age: int | None
    occupation: str | None
    onboarding_stage: OnboardingStage | None
    primary_advisor_membership_id: UUID | None
    status: ClientStatus
    created_at: datetime | None
    updated_at: datetime | None
