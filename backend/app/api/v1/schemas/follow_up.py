from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FollowUpPriority = Literal["Low", "Medium", "High"]
FollowUpStatus = Literal["Pending", "In Progress", "Completed", "Cancelled"]
FinancialPlanningStage = Literal[
    "Corporate Introduction",
    "Investment Education",
    "Tax Education",
    "Insurance Education",
    "Financial Needs Analysis",
    "Financial Plan",
]


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=2000)
    financial_planning_stage: FinancialPlanningStage
    due_date: date
    priority: FollowUpPriority = "Medium"
    status: FollowUpStatus = "Pending"

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValueError("Reason cannot be blank.")
        return reason


class FollowUpUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    financial_planning_stage: FinancialPlanningStage | None = None
    due_date: date | None = None
    priority: FollowUpPriority | None = None
    status: FollowUpStatus | None = None
    discussion_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, value: object) -> object:
        if isinstance(value, dict):
            null_fields = [
                field for field, field_value in value.items() if field_value is None
            ]
            if null_fields:
                fields = ", ".join(sorted(null_fields))
                raise ValueError(f"{fields} cannot be null.")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        reason = value.strip()
        if not reason:
            raise ValueError("Reason cannot be blank.")
        return reason

    @field_validator("discussion_notes")
    @classmethod
    def validate_discussion_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class FollowUpStatusUpdate(BaseModel):
    status: FollowUpStatus
