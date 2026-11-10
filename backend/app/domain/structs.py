# Below 50% AI-generated code

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.domain.exceptions import InvalidTimeWindowError


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        # make sure both times have a tz, otherwise we cant compare them safely
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise InvalidTimeWindowError("Time is not timezone aware.")

        # convert both times to utc so everything uses the same timezone
        object.__setattr__(self, "start_at", self.start_at.astimezone(UTC))
        object.__setattr__(self, "end_at", self.end_at.astimezone(UTC))

        # end time must be after start time
        if self.end_at <= self.start_at:
            raise InvalidTimeWindowError("End time before start time.")

        # dont allow time ranges longer than one year
        # db and meeting_type handle stricter duration checks
        if (self.end_at - self.start_at) > timedelta(days=366):
            raise InvalidTimeWindowError("Duration exceeds 1y.")

    def contains(self, other: TimeWindow) -> bool:
        return self.start_at <= other.start_at and self.end_at >= other.end_at

    @property
    def duration_minutes(self) -> int:
        return int((self.end_at - self.start_at).total_seconds() // 60)

    def overlaps(self, other: TimeWindow) -> bool:
        return self.start_at < other.end_at and other.start_at < self.end_at

    def subtract_many(self, busy_windows: list[TimeWindow]) -> list[TimeWindow]:
        """remove busy times and keep the times that are still free"""
        fragments: list[TimeWindow] = [self]

        # go through each busy time and remove it from the free parts
        for busy in busy_windows:
            next_fragments: list[TimeWindow] = []
            for frag in fragments:
                # if they dont overlap, keep the free part as it is
                if not frag.overlaps(busy):
                    next_fragments.append(frag)
                else:
                    # keep the part before/after the busy time if there is one
                    if busy.start_at > frag.start_at:
                        next_fragments.append(TimeWindow(frag.start_at, busy.start_at))
                    if busy.end_at < frag.end_at:
                        next_fragments.append(TimeWindow(busy.end_at, frag.end_at))
            # replace old free slices with the new smaller slices
            fragments = next_fragments

            # stop early if all available time has been removed
            if not fragments:
                break
        return fragments


@dataclass(frozen=True, slots=True)
class BufferConfig:
    before_minutes: int = 0
    after_minutes: int = 0

    def __post_init__(self) -> None:
        # prevent buffers from being negative or too large
        if not (0 <= self.before_minutes <= 120 and 0 <= self.after_minutes <= 120):
            raise ValueError("Buffer values before and after are invalid.")

    def expand(self, slot: TimeWindow) -> TimeWindow:
        # move the start earlier and the end later to add buffer time
        start = slot.start_at - timedelta(minutes=self.before_minutes)
        end = slot.end_at + timedelta(minutes=self.after_minutes)
        return TimeWindow(start_at=start, end_at=end)


@dataclass(frozen=True, slots=True)
class BookableSlot:
    """Represents a bookable appointment for weekly/monthly calendar views."""

    slot_window: TimeWindow
    reserved_window: TimeWindow

    @property
    def start_at(self) -> datetime:
        return self.slot_window.start_at

    @property
    def end_at(self) -> datetime:
        return self.slot_window.end_at

    @property
    def duration_minutes(self) -> int:
        return self.slot_window.duration_minutes


@dataclass(frozen=True, slots=True)
class DailyAvailabilitySummary:
    """Represents avail. info for one day."""

    calendar_date: date
    total_available_slots: int
    earliest_slot_start: datetime | None
    slots: tuple[BookableSlot, ...]
