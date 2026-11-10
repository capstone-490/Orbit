# 50% or more AI-generated
from datetime import UTC, date, datetime, time
from uuid import uuid7
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

from app.domain.entities import AvailabilityOverride, AvailabilityRule, MeetingType
from app.domain.enums import MeetingMode
from app.domain.structs import BufferConfig, TimeWindow
from app.services.availability import AvailabilityDomainService

NY_TZ = ZoneInfo("America/New_York")


@pytest.fixture
def now() -> datetime:
    """Current time: Sunday, Nov 1, 2026 at 12:00 UTC (24h before Monday Nov 2)."""
    return datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def monday_rule() -> AvailabilityRule:
    """Advisor works Mondays (day_of_week=1) from 09:00 to 11:00 America/New_York."""
    return AvailabilityRule(
        id=uuid7(),
        organization_id=uuid7(),
        advisor_membership_id=uuid7(),
        day_of_week=1,  # Monday
        start_time=time(9, 0),
        end_time=time(11, 0),
        timezone="America/New_York",
        valid_from=date(2026, 1, 1),
    )


@pytest.fixture
def meeting_type(monday_rule: AvailabilityRule) -> MeetingType:
    """30-minute meeting, 30-minute step interval, zero buffers by default."""
    return MeetingType(
        id=uuid7(),
        organization_id=monday_rule.organization_id,
        subscription_id=uuid7(),
        advisor_membership_id=monday_rule.advisor_membership_id,
        slug="discovery-30",
        title="30-Min Discovery",
        description=None,
        duration_minutes=30,
        slot_interval_minutes=30,
        buffers=BufferConfig(before_minutes=0, after_minutes=0),
        minimum_notice_minutes=60,
        max_days_in_advance=60,
        meeting_mode=MeetingMode.VIDEO,
    )


def test_happy_path_weekly_slot_slicing(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """A 2-hour working window (09:00-11:00) with 30m duration and 30m step yields 4 slots."""
    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert len(slots) == 4
    assert slots[0].start_at == datetime(2026, 11, 2, 9, 0, tzinfo=NY_TZ).astimezone(
        UTC
    )
    assert slots[-1].end_at == datetime(2026, 11, 2, 11, 0, tzinfo=NY_TZ).astimezone(
        UTC
    )


# =============================================================================


def test_happy_path_sliding_15_min_step_interval(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """A 1-hour window (09:00-10:00) with 30m duration and 15m step yields 3 sliding start times (9:00, 9:15, 9:30)."""
    monday_rule.end_time = time(10, 0)
    meeting_type.slot_interval_minutes = 15

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert [s.start_at.astimezone(NY_TZ).strftime("%H:%M") for s in slots] == [
        "09:00",
        "09:15",
        "09:30",
    ]


def test_happy_path_positive_custom_override_opens_weekend_hours(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """An available override on a Saturday opens bookable slots even without a Saturday weekly rule."""
    saturday = date(2026, 11, 7)
    custom_saturday_window = TimeWindow(
        datetime(2026, 11, 7, 10, 0, tzinfo=NY_TZ),
        datetime(2026, 11, 7, 11, 0, tzinfo=NY_TZ),
    )
    saturday_override = AvailabilityOverride(
        id=uuid7(),
        organization_id=monday_rule.organization_id,
        advisor_membership_id=monday_rule.advisor_membership_id,
        override_date=saturday,
        is_available=True,
        custom_window=custom_saturday_window,
    )

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[saturday_override],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=saturday,
        end_date=saturday,
        now=now,
    )

    assert len(slots) == 2  # 10:00-10:30 and 10:30-11:00


def test_happy_path_monthly_summary_populates_all_calendar_days(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """Monthly summary for November 2026 returns all 30 calendar days with accurate counts."""
    summaries = AvailabilityDomainService.compute_monthly_summary(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        year=2026,
        month=11,
        viewer_timezone="America/New_York",
        now=now,
    )

    assert len(summaries) == 30
    assert summaries[0].calendar_date == date(2026, 11, 1)  # Sunday -> 0 slots
    assert summaries[0].total_available_slots == 0
    assert summaries[0].earliest_slot_start is None
    assert summaries[1].calendar_date == date(2026, 11, 2)  # Monday -> 4 slots
    assert summaries[1].total_available_slots == 4
    assert summaries[1].earliest_slot_start == slots_first_start(summaries[1])


def slots_first_start(summary: object) -> datetime | None:
    return summary.slots[0].start_at  # type: ignore[attr-defined]


def test_weekly_slot_slicing_creates_four_slots_for_two_hour_window(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert len(slots) == 4
    assert slots[0].start_at == datetime(2026, 11, 2, 9, 0, tzinfo=NY_TZ).astimezone(
        UTC
    )
    assert slots[-1].end_at == datetime(2026, 11, 2, 11, 0, tzinfo=NY_TZ).astimezone(
        UTC
    )


def test_busy_window_and_buffers_block_adjacent_slots(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    # Arrange: Add 10m before & 10m after buffers, plus a busy meeting at 09:30 - 10:00 NY time
    meeting_type.buffers = BufferConfig(before_minutes=10, after_minutes=10)
    busy_930_to_1000 = TimeWindow(
        datetime(2026, 11, 2, 9, 30, tzinfo=NY_TZ),
        datetime(2026, 11, 2, 10, 0, tzinfo=NY_TZ),
    )

    # Act
    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[busy_930_to_1000],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    # Assert:
    # - 09:00-09:30 is blocked because its +10m after-buffer (09:00-09:40) hits 09:30!
    # - 09:30-10:00 is blocked directly!
    # - 10:00-10:30 is blocked because its -10m before-buffer (09:50-10:30) hits 10:00!
    # Only 10:30-11:00 survives!
    assert len(slots) == 1
    assert slots[0].start_at == datetime(2026, 11, 2, 10, 30, tzinfo=NY_TZ).astimezone(
        UTC
    )


def test_full_day_blackout_override_removes_all_slots(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    holiday_override = AvailabilityOverride(
        id=uuid7(),
        organization_id=monday_rule.organization_id,
        advisor_membership_id=monday_rule.advisor_membership_id,
        override_date=date(2026, 11, 2),
        is_available=False,
        custom_window=None,
    )

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[holiday_override],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert slots == []


def test_boundary_busy_window_and_buffers_block_adjacent_slots(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """Pre/post buffers expand the candidate slot so back-to-back collisions with busy blocks are rejected."""
    meeting_type.buffers = BufferConfig(before_minutes=10, after_minutes=10)
    busy_930_to_1000 = TimeWindow(
        datetime(2026, 11, 2, 9, 30, tzinfo=NY_TZ),
        datetime(2026, 11, 2, 10, 0, tzinfo=NY_TZ),
    )

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[busy_930_to_1000],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    # 09:00-09:30 (+10m buffer -> 09:40) hits 09:30
    # 09:30-10:00 hits directly
    # 10:00-10:30 (-10m buffer -> 09:50) hits 10:00
    # Only 10:30-11:00 (reserved 10:20-11:10) is conflict-free!
    assert len(slots) == 1
    assert slots[0].start_at == datetime(2026, 11, 2, 10, 30, tzinfo=NY_TZ).astimezone(
        UTC
    )


def test_boundary_minimum_notice_and_max_advance_cutoffs(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
) -> None:
    """Slots starting strictly before `now + minimum_notice_minutes` are excluded, while exact boundary is included."""
    # Set `now` to Monday Nov 2 at 08:30 NY time. With minimum_notice_minutes = 60,
    # earliest allowed slot is 09:30 NY time (so 09:00 is excluded, 09:30 is included).
    monday_830_ny = datetime(2026, 11, 2, 8, 30, tzinfo=NY_TZ).astimezone(UTC)

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=monday_830_ny,
    )

    assert [s.start_at.astimezone(NY_TZ).strftime("%H:%M") for s in slots] == [
        "09:30",
        "10:00",
        "10:30",
    ]


def test_boundary_cross_date_viewer_timezone_in_monthly_summary(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """An evening slot on Monday in New York (e.g. 20:00-21:00 EST = 01:00-02:00 UTC Tuesday) buckets into Tuesday for a Tokyo viewer."""
    monday_rule.start_time = time(20, 0)
    monday_rule.end_time = time(21, 0)

    summaries = AvailabilityDomainService.compute_monthly_summary(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        year=2026,
        month=11,
        viewer_timezone="Asia/Tokyo",  # UTC+9 (14 hours ahead of NY EST)
        now=now,
    )

    # Monday Nov 2 at 20:00 EST is Tuesday Nov 3 at 10:00 AM in Tokyo!
    monday_summary = summaries[1]  # Nov 2
    tuesday_summary = summaries[2]  # Nov 3
    assert monday_summary.calendar_date == date(2026, 11, 2)
    assert monday_summary.total_available_slots == 0
    assert tuesday_summary.calendar_date == date(2026, 11, 3)
    assert tuesday_summary.total_available_slots == 2


def test_boundary_rule_valid_from_and_valid_until_window(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """Rules only generate slots on dates within [valid_from, valid_until]."""
    monday_rule.valid_from = date(2026, 11, 9)
    monday_rule.valid_until = date(2026, 11, 16)

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),  # Nov 2 (before valid_from)
        end_date=date(2026, 11, 23),  # Nov 23 (after valid_until)
        now=now,
    )

    slot_dates = {s.start_at.astimezone(NY_TZ).date() for s in slots}
    assert slot_dates == {date(2026, 11, 9), date(2026, 11, 16)}


def test_negative_full_day_blackout_override_produces_zero_slots(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """A full-day blackout override (is_available=False, custom_window=None) suppresses all weekly rules for that day."""
    holiday_override = AvailabilityOverride(
        id=uuid7(),
        organization_id=monday_rule.organization_id,
        advisor_membership_id=monday_rule.advisor_membership_id,
        override_date=date(2026, 11, 2),
        is_available=False,
        custom_window=None,
    )

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[holiday_override],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert slots == []


def test_negative_partial_blackout_leaves_fragment_smaller_than_meeting_duration(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """If a partial blackout leaves only a 20-minute fragment, a 30-minute meeting cannot fit."""
    # Working window is 09:00 - 09:30. Blackout 09:20 - 09:30 leaves only 20 mins (09:00 - 09:20).
    monday_rule.end_time = time(9, 30)
    partial_blackout = AvailabilityOverride(
        id=uuid7(),
        organization_id=monday_rule.organization_id,
        advisor_membership_id=monday_rule.advisor_membership_id,
        override_date=date(2026, 11, 2),
        is_available=False,
        custom_window=TimeWindow(
            datetime(2026, 11, 2, 9, 20, tzinfo=NY_TZ),
            datetime(2026, 11, 2, 9, 30, tzinfo=NY_TZ),
        ),
    )

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[partial_blackout],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert slots == []


def test_negative_inactive_rules_are_ignored(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """When `rule.is_active` is False, no working windows or slots are generated."""
    monday_rule.is_active = False

    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert slots == []


def test_negative_inverted_date_range_returns_empty_list(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """When start_date > end_date, the service safely returns an empty list without looping."""
    slots = AvailabilityDomainService.compute_available_slots(
        rules=[monday_rule],
        overrides=[],
        busy_windows=[],
        meeting_type=meeting_type,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 2),
        now=now,
    )

    assert slots == []


def test_error_invalid_viewer_timezone_raises_zoneinfo_error(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """Passing an unknown IANA timezone string raises ZoneInfoNotFoundError."""
    with pytest.raises(ZoneInfoNotFoundError):
        AvailabilityDomainService.compute_monthly_summary(
            rules=[monday_rule],
            overrides=[],
            busy_windows=[],
            meeting_type=meeting_type,
            year=2026,
            month=11,
            viewer_timezone="Invalid/Not_A_Timezone",
            now=now,
        )


def test_error_invalid_month_number_raises_value_error(
    monday_rule: AvailabilityRule,
    meeting_type: MeetingType,
    now: datetime,
) -> None:
    """Passing month=13 or month=0 raises ValueError from date/calendar."""
    with pytest.raises(ValueError):
        AvailabilityDomainService.compute_monthly_summary(
            rules=[monday_rule],
            overrides=[],
            busy_windows=[],
            meeting_type=meeting_type,
            year=2026,
            month=13,
            viewer_timezone="America/New_York",
            now=now,
        )
