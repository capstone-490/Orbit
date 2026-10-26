from datetime import datetime, time, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SLA_WINDOW = timedelta(hours=24)


class UrgencyState(Enum):
    DUE_NOW = "DUE_NOW"
    UPCOMING = "UPCOMING"
    RESOLVED = "RESOLVED"


URGENCY_COLOR = {
    UrgencyState.DUE_NOW: "red",
    UrgencyState.UPCOMING: "yellow",
    UrgencyState.RESOLVED: "green",
}

def get_timezone(location: str | None):
    if not location:
         return ZoneInfo("UTC")
    try:
        return ZoneInfo(location)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown timezone: {location}")


def force_utc(date_time: datetime):
    if date_time.tzinfo is None:
        raise ValueError("Need datetime with TimeZone")
    return date_time.astimezone(timezone.utc)


def total_weekend_time(start: datetime, end: datetime, time_zone: ZoneInfo):

    total = timedelta(0)
    if(start < end):
        start_day = start.astimezone(time_zone).date()
        last_day = end.astimezone(time_zone).date()
        start_weekday = start_day.weekday
        last_weekday = last_day.weekday
        if (start_weekday + (start_day-last_day).days) >= 5:
            
    return total

def counted_time_remaining(now: datetime, due: datetime, tz: ZoneInfo) -> timedelta:
    now, due = force_utc(now), force_utc(due)
    if due <= now:
        return timedelta(0)
    return (due - now) - _weekend_overlap(now, due, tz)


def compute_urgency(
    status: str,
    due_date: datetime,
    tz: ZoneInfo,
    now: datetime | None = None,
) -> UrgencyState:
    if status == "Resolved":
        return UrgencyState.RESOLVED
    now = now or datetime.now(timezone.utc)
    if force_utc(due_date) <= force_utc(now):
        return UrgencyState.DUE_NOW
    if counted_time_remaining(now, due_date, tz) < SLA_WINDOW:
        return UrgencyState.DUE_NOW
    return UrgencyState.UPCOMING