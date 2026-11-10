# 50% or more AI-generated code

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import DBAPIError

from app.domain.structs import TimeWindow

PG_EXCLUSION_VIOLATION_SQLSTATE = "23P01"
PG_UNIQUE_VIOLATION_SQLSTATE = "23505"


# pg uses tstzrange to store time ranges with tz info
# convert our domain time window into the format pg expects
def _to_pg_tstzrange(window: TimeWindow) -> Range[datetime]:
    """Converts TimeWindow into sqlalchemy pgsql [start, end) Range."""
    return Range(
        lower=window.start_at,
        upper=window.end_at,
        bounds="[)",
        empty=False,
    )


# convert the database range back into our own time window object
# reject unbounded ranges since our time windows need a start and end
def _from_pg_tstzrange(pg_range: Range[datetime]) -> TimeWindow:
    """Converts sqlalchemy pgsgql Range into TimeWindow."""
    if pg_range.lower is None or pg_range.upper is None:
        raise ValueError("Database returned an unbounded tstzrange.")
    return TimeWindow(start_at=pg_range.lower, end_at=pg_range.upper)


# pg uses sqlstate 23p01 when an exclusion constraint is violated
# check the error code to detect overlapping bookings or meetings
def _is_exclusion_violation(exc: DBAPIError) -> bool:
    """
    Detects PostgreSQL SQLSTATE 23P01 raised by:
      1. excl_bookings_no_advisor_overlap GiST constraint, OR
      2. trg_bookings_jit_evict_and_check_meetings trigger, OR
      3. trg_meetings_check_booking_conflicts trigger, OR
      4. excl_meetings_no_advisor_busy_overlap GiST constraint.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate == PG_EXCLUSION_VIOLATION_SQLSTATE:
        return True
    error_text = str(exc)
    return (
        PG_EXCLUSION_VIOLATION_SQLSTATE in error_text
        or "excl_bookings_no_advisor_overlap" in error_text
        or "excl_meetings_no_advisor_busy_overlap" in error_text
    )


# check for duplicate records using pg unique violation code
def _is_unique_violation(exc: DBAPIError, constraint_name: str | None = None) -> bool:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate == PG_UNIQUE_VIOLATION_SQLSTATE:
        if constraint_name is None:
            return True
        return constraint_name in str(exc)
    return constraint_name is not None and constraint_name in str(exc)
