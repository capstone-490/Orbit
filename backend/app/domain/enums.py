# No substantial AI-generated code

from enum import StrEnum


class BookingStatus(StrEnum):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class MeetingMode(StrEnum):
    VIDEO = "video"
    PHONE = "phone"
    IN_PERSON = "in_person"


class ClientStatus(StrEnum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OnboardingStage(StrEnum):
    CORPORATE_INTRODUCTION = "corporate_introduction"
    INVESTMENT_EDUCATION = "investment_education"
    TAX_EDUCATION = "tax_education"
    INSURANCE_EDUCATION = "insurance_education"
    FINANCIAL_NEEDS_ANALYSIS = "financial_needs_analysis"
    FINANCIAL_PLAN = "financial_plan"
