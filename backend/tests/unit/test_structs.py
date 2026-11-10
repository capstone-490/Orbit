# 50% or more AI-generated code
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.exceptions import InvalidTimeWindowError
from app.domain.structs import (
    BookableSlot,
    BufferConfig,
    DailyAvailabilitySummary,
    TimeWindow,
)


# =============================================================================
# TimeWindow: Construction, Validation & Timezone Normalization
# =============================================================================
def test_time_window_normalizes_timezones_to_utc_and_computes_duration() -> None:
    ny_tz = ZoneInfo("America/New_York")
    # 2026-11-10 is EST (UTC-5): 09:00 EST -> 14:00 UTC, 10:30 EST -> 15:30 UTC
    start_est = datetime(2026, 11, 10, 9, 0, tzinfo=ny_tz)
    end_est = datetime(2026, 11, 10, 10, 30, tzinfo=ny_tz)

    window = TimeWindow(start_at=start_est, end_at=end_est)

    assert window.start_at == datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
    assert window.end_at == datetime(2026, 11, 10, 15, 30, tzinfo=UTC)
    assert window.start_at.tzinfo == UTC
    assert window.end_at.tzinfo == UTC
    assert window.duration_minutes == 90


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        # Naive start_at
        (
            datetime(2026, 11, 10, 9, 0),
            datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
        ),
        # Naive end_at
        (
            datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 10, 0),
        ),
        # Both naive
        (
            datetime(2026, 11, 10, 9, 0),
            datetime(2026, 11, 10, 10, 0),
        ),
    ],
)
def test_time_window_rejects_naive_datetimes(
    start_at: datetime,
    end_at: datetime,
) -> None:
    with pytest.raises(InvalidTimeWindowError, match="not timezone aware"):
        TimeWindow(start_at=start_at, end_at=end_at)


@pytest.mark.parametrize(
    ("start_at", "end_at"),
    [
        # Zero duration (end == start)
        (
            datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
        ),
        # Negative duration (end < start)
        (
            datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
        ),
    ],
)
def test_time_window_rejects_non_positive_duration(
    start_at: datetime,
    end_at: datetime,
) -> None:
    with pytest.raises(InvalidTimeWindowError, match="End time before start time"):
        TimeWindow(start_at=start_at, end_at=end_at)


def test_time_window_is_immutable() -> None:
    start = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    window = TimeWindow(start, start + timedelta(minutes=30))

    with pytest.raises(FrozenInstanceError):
        window.start_at = start + timedelta(minutes=15)  # type: ignore[misc]


# =============================================================================
# TimeWindow: Half-Open [start, end) Containment & Overlap Semantics
# =============================================================================
def test_time_window_contains() -> None:
    base = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    outer = TimeWindow(base, base + timedelta(hours=2))  # [09:00, 11:00)

    # Identical bounds -> True
    assert outer.contains(TimeWindow(base, base + timedelta(hours=2))) is True
    # Strict interior -> True
    assert (
        outer.contains(
            TimeWindow(
                base + timedelta(minutes=15),
                base + timedelta(minutes=45),
            )
        )
        is True
    )
    # Spilling past end by 1 minute -> False
    assert (
        outer.contains(
            TimeWindow(
                base + timedelta(hours=1),
                base + timedelta(hours=2, minutes=1),
            )
        )
        is False
    )
    # Starting 1 minute before -> False
    assert (
        outer.contains(
            TimeWindow(
                base - timedelta(minutes=1),
                base + timedelta(hours=1),
            )
        )
        is False
    )


def test_time_window_overlaps_respects_half_open_boundaries() -> None:
    t09_00 = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    t09_30 = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)
    t10_00 = datetime(2026, 11, 10, 10, 0, tzinfo=UTC)
    t10_30 = datetime(2026, 11, 10, 10, 30, tzinfo=UTC)

    first = TimeWindow(t09_00, t10_00)  # [09:00, 10:00)
    adjacent = TimeWindow(t10_00, t10_30)  # [10:00, 10:30)
    overlapping = TimeWindow(t09_30, t10_30)  # [09:30, 10:30)

    # Half-open intervals touching at 10:00 do NOT overlap
    assert first.overlaps(adjacent) is False
    assert adjacent.overlaps(first) is False

    # Intervals sharing [09:30, 10:00) DO overlap
    assert first.overlaps(overlapping) is True
    assert overlapping.overlaps(first) is True


# =============================================================================
# TimeWindow: Multi-Interval Subtraction (`subtract_many`)
# =============================================================================
def test_subtract_many_with_no_or_disjoint_busy_windows_returns_original() -> None:
    t09 = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    t12 = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    work_morning = TimeWindow(t09, t12)

    assert work_morning.subtract_many([]) == [work_morning]

    # Touching before [08:00, 09:00) and touching after [12:00, 13:00)
    before = TimeWindow(t09 - timedelta(hours=1), t09)
    after = TimeWindow(t12, t12 + timedelta(hours=1))
    assert work_morning.subtract_many([before, after]) == [work_morning]


def test_subtract_many_trims_edges_and_splits_interior() -> None:
    # Available window: [09:00, 17:00)
    day_start = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    day_end = datetime(2026, 11, 10, 17, 0, tzinfo=UTC)
    workday = TimeWindow(day_start, day_end)

    busy_windows = [
        # 1. Overlaps start: [08:30, 09:30) -> trims start to 09:30
        TimeWindow(
            datetime(2026, 11, 10, 8, 30, tzinfo=UTC),
            datetime(2026, 11, 10, 9, 30, tzinfo=UTC),
        ),
        # 2. Interior meeting: [11:00, 12:00) -> splits middle
        TimeWindow(
            datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
        ),
        # 3. Overlapping/unsorted afternoon busy blocks: [14:00, 15:00) and [14:30, 15:30)
        TimeWindow(
            datetime(2026, 11, 10, 14, 30, tzinfo=UTC),
            datetime(2026, 11, 10, 15, 30, tzinfo=UTC),
        ),
        TimeWindow(
            datetime(2026, 11, 10, 14, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 15, 0, tzinfo=UTC),
        ),
        # 4. Overlaps end: [16:30, 17:30) -> trims end to 16:30
        TimeWindow(
            datetime(2026, 11, 10, 16, 30, tzinfo=UTC),
            datetime(2026, 11, 10, 17, 30, tzinfo=UTC),
        ),
    ]

    free_fragments = workday.subtract_many(busy_windows)

    assert free_fragments == [
        TimeWindow(
            datetime(2026, 11, 10, 9, 30, tzinfo=UTC),
            datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
        ),
        TimeWindow(
            datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
            datetime(2026, 11, 10, 14, 0, tzinfo=UTC),
        ),
        TimeWindow(
            datetime(2026, 11, 10, 15, 30, tzinfo=UTC),
            datetime(2026, 11, 10, 16, 30, tzinfo=UTC),
        ),
    ]


def test_subtract_many_when_fully_covered_returns_empty_list() -> None:
    window = TimeWindow(
        datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
        datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
    )
    covering_busy = TimeWindow(
        datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
        datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    )

    assert window.subtract_many([covering_busy]) == []


# =============================================================================
# BufferConfig: Validation & Slot Expansion
# =============================================================================
def test_buffer_config_defaults_and_expands_slot() -> None:
    default_buf = BufferConfig()
    assert default_buf.before_minutes == 0
    assert default_buf.after_minutes == 0

    slot = TimeWindow(
        datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
        datetime(2026, 11, 10, 10, 30, tzinfo=UTC),
    )
    assert default_buf.expand(slot) == slot

    asym_buf = BufferConfig(before_minutes=5, after_minutes=10)
    expanded = asym_buf.expand(slot)
    assert expanded == TimeWindow(
        datetime(2026, 11, 10, 9, 55, tzinfo=UTC),
        datetime(2026, 11, 10, 10, 40, tzinfo=UTC),
    )
    assert expanded.duration_minutes == 45


@pytest.mark.parametrize(
    ("before_minutes", "after_minutes"),
    [
        (-1, 0),
        (0, -5),
        (121, 0),
        (0, 121),
    ],
)
def test_buffer_config_rejects_out_of_range_minutes(
    before_minutes: int,
    after_minutes: int,
) -> None:
    with pytest.raises(ValueError, match="Buffer values before and after are invalid"):
        BufferConfig(before_minutes=before_minutes, after_minutes=after_minutes)


# =============================================================================
# BookableSlot & DailyAvailabilitySummary: Properties & Structure
# =============================================================================
def test_bookable_slot_and_daily_availability_summary_properties() -> None:
    slot_window = TimeWindow(
        datetime(2026, 11, 10, 14, 0, tzinfo=UTC),
        datetime(2026, 11, 10, 14, 30, tzinfo=UTC),
    )
    buffers = BufferConfig(before_minutes=5, after_minutes=10)
    reserved_window = buffers.expand(slot_window)

    bookable = BookableSlot(
        slot_window=slot_window,
        reserved_window=reserved_window,
    )

    # BookableSlot properties reflect the client-facing slot_window, not the buffered reserved_window
    assert bookable.start_at == slot_window.start_at
    assert bookable.end_at == slot_window.end_at
    assert bookable.duration_minutes == 30
    assert bookable.reserved_window.duration_minutes == 45

    summary = DailyAvailabilitySummary(
        calendar_date=date(2026, 11, 10),
        total_available_slots=1,
        earliest_slot_start=bookable.start_at,
        slots=(bookable,),
    )
    assert summary.calendar_date == date(2026, 11, 10)
    assert summary.total_available_slots == 1
    assert summary.earliest_slot_start == slot_window.start_at
    assert summary.slots == (bookable,)


def test_start_eq_end_raises():
    start_at = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
    end_at = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
    with pytest.raises(InvalidTimeWindowError):
        TimeWindow(start_at, end_at)


def test_start_gt_end_raises():
    start_at = datetime(2026, 10, 27, 11, 0, tzinfo=UTC)
    end_at = datetime(2026, 10, 27, 10, 0, tzinfo=UTC)

    with pytest.raises(InvalidTimeWindowError):
        TimeWindow(start_at, end_at)


def test_normalizes_non_utc_aware_datetimes_to_utc() -> None:
    new_york = ZoneInfo("America/New_York")
    start_at = datetime(2026, 10, 27, 9, 0, tzinfo=new_york)
    end_at = datetime(2026, 10, 27, 9, 30, tzinfo=new_york)

    window = TimeWindow(start_at, end_at)

    assert window.start_at.tzinfo == UTC
    assert window.end_at.tzinfo == UTC

    # Verify that normalization preserves the actual instants.
    assert window.start_at == start_at.astimezone(UTC)
    assert window.end_at == end_at.astimezone(UTC)


def test_half_open_overlap_false():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 10, 00, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 10, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 11, 00, tzinfo=UTC),
    )

    assert tw1.overlaps(tw2) == False


def test_half_open_overlap_true():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 10, 1, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 10, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 11, 00, tzinfo=UTC),
    )

    assert tw1.overlaps(tw2) == True


def test_interval_subsctraction_middle():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 17, 00, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 13, 00, tzinfo=UTC),
    )

    r1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 12, 00, tzinfo=UTC),
    )
    r2 = TimeWindow(
        datetime(2026, 10, 27, 13, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 17, 00, tzinfo=UTC),
    )
    assert tw1.subtract_many([tw2]) == [r1, r2]


def test_interval_subsctraction_edge_trim():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 17, 0, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 8, 30, tzinfo=UTC),
        datetime(2026, 10, 27, 9, 30, tzinfo=UTC),
    )
    tw3 = TimeWindow(
        datetime(2026, 10, 27, 16, 30, tzinfo=UTC),
        datetime(2026, 10, 27, 18, 00, tzinfo=UTC),
    )

    r1 = TimeWindow(
        datetime(2026, 10, 27, 9, 30, tzinfo=UTC),
        datetime(2026, 10, 27, 16, 30, tzinfo=UTC),
    )
    assert tw1.subtract_many([tw2, tw3]) == [r1]


def test_interval_subsctraction_wipe():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 8, 00, tzinfo=UTC),
        datetime(2026, 10, 27, 13, 30, tzinfo=UTC),
    )
    assert tw1.subtract_many([tw2]) == []


def test_interval_subsctraction_overlap():
    tw1 = TimeWindow(
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 27, 17, 0, tzinfo=UTC),
    )
    tw2 = TimeWindow(
        datetime(2026, 10, 27, 10, 00, tzinfo=UTC),
        datetime(2026, 10, 27, 11, 30, tzinfo=UTC),
    )
    tw3 = TimeWindow(
        datetime(2026, 10, 27, 11, 00, tzinfo=UTC),
        datetime(2026, 10, 27, 12, 00, tzinfo=UTC),
    )

    r1 = TimeWindow(
        datetime(2026, 10, 27, 9, 00, tzinfo=UTC),
        datetime(2026, 10, 27, 10, 00, tzinfo=UTC),
    )
    r2 = TimeWindow(
        datetime(2026, 10, 27, 12, 00, tzinfo=UTC),
        datetime(2026, 10, 27, 17, 00, tzinfo=UTC),
    )
    assert tw1.subtract_many([tw2, tw3]) == [r1, r2]
