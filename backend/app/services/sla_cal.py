from datetime import datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SLA_WINDOW = timedelta(hours=24)


class UrgencyState(Enum):
    DUE_NOW = "DUE_NOW"
    UPCOMING = "UPCOMING"
    RESOLVED = "RESOLVED"

FRIDAY_WEEKDAY = 4

URGENCY_COLOR = {
    UrgencyState.DUE_NOW: "Red",
    UrgencyState.UPCOMING: "Yellow",
    UrgencyState.RESOLVED: "Green",
}

def get_timezone(location: str):
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

#Count deltatime between two dates excluding any weekend time
def count_timedelta_between_dates(start_dt: datetime, end_dt: datetime, tz: ZoneInfo):
    adjusted_start_dt = start_dt.astimezone(tz)
    adjusted_end_dt = end_dt.astimezone(tz)

    print(adjusted_start_dt)
    print(adjusted_end_dt)

    if(adjusted_start_dt > adjusted_end_dt):
        return timedelta(0)

    #Remove weekend uncertainty from the end datetime
    if(adjusted_end_dt.weekday() > FRIDAY_WEEKDAY):
        added_days = timedelta(days = (3-(adjusted_end_dt.weekday()-FRIDAY_WEEKDAY)))
        adjusted_end_dt = (adjusted_end_dt + added_days).replace(hour=0, minute=0, second=0, microsecond=0)

    #Remove weekend uncertainty from the start datetime
    if(adjusted_start_dt.weekday() > FRIDAY_WEEKDAY):
        added_days = timedelta(days = (3-(adjusted_start_dt.weekday()-FRIDAY_WEEKDAY)))
        adjusted_start_dt = (adjusted_start_dt + added_days).replace(hour=0, minute=0, second=0, microsecond=0)

    current_date = adjusted_start_dt.date()
    end_date = adjusted_end_dt.date()
    weekend_days = 0
    while current_date < end_date:
        if current_date.weekday() >= 5:
            weekend_days += 1
        current_date += timedelta(days=1)

    time_between_dates = (adjusted_end_dt - adjusted_start_dt) - timedelta(days = weekend_days)

    return time_between_dates

def compute_urgency(status: str, due_date: datetime, tz: ZoneInfo, now: datetime | None = None,) -> UrgencyState:
    if status == "Resolved":
        return UrgencyState.RESOLVED
    now = now or datetime.now(timezone.utc)
    if force_utc(due_date) <= force_utc(now):
        return UrgencyState.DUE_NOW
    if count_timedelta_between_dates(now, due_date, tz) <= SLA_WINDOW:
        return UrgencyState.DUE_NOW
    return UrgencyState.UPCOMING