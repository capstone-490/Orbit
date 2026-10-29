
import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.sla_cal import (
    SLA_WINDOW,
    UrgencyState,
    get_timezone,
    force_utc,
    count_timedelta_between_dates,
    compute_urgency,
)


def test_true_ZoneInfo_get_timezone():
    tz = get_timezone("America/New_York")

    assert isinstance(tz, ZoneInfo)
    assert tz.key == "America/New_York"


def test_nonexistence_get_timezone():
    with pytest.raises(ValueError, match="Unknown timezone: Invalid/Timezone"):
        get_timezone("Invalid/Timezone")


def test_null_get_timezone():
    tz = get_timezone(None)

    assert isinstance(tz, ZoneInfo)
    assert tz.key == "UTC"


def test_true_none_ZoneInfo_get_timezone():
    tz = get_timezone("UTC")

    assert isinstance(tz, ZoneInfo)
    assert tz.key == "UTC"

def test_no_timezone_datetime_force_utc():
    dt = datetime(2026, 1, 1, 12, 0, 0)

    with pytest.raises(ValueError, match="Need datetime with TimeZone"):
        force_utc(dt)

def test_timezone_with_timezone_force_utc():
    dt = datetime(
        2026, 1, 1, 12, 0, 0,
        tzinfo=ZoneInfo("America/New_York"),
    )

    result = force_utc(dt)

    assert result == datetime(2026, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc

def test_two_weekday_date_count_timedelta_between_dates():
    tz = ZoneInfo("UTC")
    start = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(days=8)


def test_one_weekday_one_weekend_date_count_timedelta_between_date():
    tz = ZoneInfo("UTC")
    start = datetime(2026, 1, 9, 9, 0, tzinfo=timezone.utc)   # Friday
    end = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)    # Sunday

    result = count_timedelta_between_dates(start, end, tz)

    # Sunday is normalized to Monday at midnight by the implementation.
    assert result == timedelta(hours=15)


def test_two_weekends_date_count_timedelta_between_date():
    tz = ZoneInfo("UTC")
    start = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 24, 9, 0, tzinfo=timezone.utc)

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(days=10)

def test_leap_year_date_count_timedelta_between_date():
    tz = ZoneInfo("UTC")
    start = datetime(2028, 2, 1, 9, 0, tzinfo=timezone.utc)
    end = datetime(2028, 3, 1, 9, 0, tzinfo=timezone.utc)

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(days=21)

#Changing to New York should move both from Saturday to Fridays with
# starting having a later hour than ending
def test_different_timezones_count_timedelta_between_date():
    tz = ZoneInfo("America/New_York")
    start = datetime(2026, 1, 10, 4, 0, tzinfo=ZoneInfo("Europe/Vienna"))
    end = datetime(2026, 1, 24, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(days=9, hours=22)

#DST is always on Sundays, as our count_timedelta_between_date remove time
#used by Saturday and Sunday, it means that DST has no effect on our system
def test_daylight_saving_time_count_timedelta_between_date():
    tz = ZoneInfo("UTC")
    start = datetime(2026, 3, 8, 9, 0, tzinfo=ZoneInfo("America/New_York"))
    end = datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc)

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(days=3, hours=10)


def test_end_date_before_start_count_timedelta_between_date():
    tz = ZoneInfo("UTC")
    start = datetime(2026, 1, 7, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)

    result = count_timedelta_between_dates(start, end, tz)

    assert result == timedelta(0)

def test_resolved_compute_urgency():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    due_date = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)

    result = compute_urgency("Resolved", due_date, tz, now)

    assert result == UrgencyState.RESOLVED


def test_end_date_before_start_compute_urgency():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    due_date = datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc)

    result = compute_urgency("Open", due_date, tz, now)

    assert result == UrgencyState.DUE_NOW


def test_null_now_argument_compute_urgency():
    tz = ZoneInfo("UTC")
    due_date = datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc)

    result = compute_urgency("Open", due_date, tz, None)

    assert result == UrgencyState.DUE_NOW


def test_time_more_than_24h_compute_urgency():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    due_date = datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc)

    result = compute_urgency("Open", due_date, tz, now)

    # More than 24 hours away, excluding weekends.
    assert result == UrgencyState.UPCOMING


def test_time_equal_24h_compute_urgency():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    due_date = now + SLA_WINDOW

    result = compute_urgency("Open", due_date, tz, now)

    assert result == UrgencyState.DUE_NOW


def test_time_less_than_24h_compute_urgency():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    due_date = now + timedelta(hours=12)

    result = compute_urgency("Open", due_date, tz, now)

    assert result == UrgencyState.DUE_NOW
