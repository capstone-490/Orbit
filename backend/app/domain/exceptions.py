# No substantial AI-generated code


class DomainError(Exception):
    """Base exception for all domain errors."""


class AuthenticationError(DomainError):
    """401 Unauthorized: missing, expired, or invalid authentication."""


class AuthorizationDenied(DomainError):
    """403 Forbidden: authenticated caller lacks required permission."""


class ResourceNotFoundError(DomainError):
    """404 Not Found: missing resource or concealed foreign-tenant resource."""


class AuthorizationServiceUnavailable(DomainError):
    """503 Service Unavailable: OpenFGA or policy engine unreachable (fail-closed)."""


class BookingDomainError(DomainError):
    """Base exception for booking errors."""


class InvalidTimeWindowError(BookingDomainError):
    """422 Unprocessable Content: end_time < start_time or duration > 24h"""


class BookingLinkInvalidError(BookingDomainError):
    """404: public_token does not exist/inactive/expired or advisor/org is disabled"""


class InvalidSlotSelectionError(BookingDomainError):
    """422: slot violates minimum_notice_minutes, exceeds max_days_in_advance, or outside working hours."""


class SlotOverlapConflictError(BookingDomainError):
    """409 Conflict: PGSQL throws SQLSTATE 23P01."""


class HoldExpiredError(BookingDomainError):
    """410 Gone: prospect tries to book after hold expires."""


class InvalidCancellationTokenError(BookingDomainError):
    """404: public cancellation token unknown or booking already cancelled."""


class ClientNotFoundError(BookingDomainError):
    """404: client record does not exist in the specified tenant/subscription."""


class DuplicateClientEmailError(BookingDomainError):
    """409: when an active client in the same subscription already uses the email."""
