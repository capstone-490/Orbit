# 50% or more AI-generated code
import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.entities import AvailabilityOverride, AvailabilityRule, MeetingType
from app.domain.structs import BookableSlot, DailyAvailabilitySummary, TimeWindow


class AvailabilityDomainService:
    """
    Stateless service that computes booking times from
    advisor availability rules in their tz, applying overrides,
    and checking busy blocks.
    """

    @staticmethod
    def resolve_working_windows(
        *,
        rules: list[AvailabilityRule],
        overrides: list[AvailabilityOverride],
        start_date: date,
        end_date: date,
    ) -> list[TimeWindow]:
        """
        find the working hours for each day
        apply custom hours and remove blocked time ranges
        """

        # group overrides by date so we can find them faster
        overrides_by_date: dict[date, list[AvailabilityOverride]] = defaultdict(list)
        for override in overrides:
            overrides_by_date[override.override_date].append(override)

        # group active rules by weekday for easier lookup
        rules_by_dow: dict[int, list[AvailabilityRule]] = defaultdict(list)
        for rule in rules:
            if rule.is_active:
                rules_by_dow[rule.day_of_week].append(rule)

        working_windows: list[TimeWindow] = []
        current_date = start_date

        # go through every date in the requested range
        while current_date <= end_date:
            todays_overrides = overrides_by_date.get(current_date, [])

            # check if the whole day is blocked
            has_full_day_blackout = any(
                not ov.is_available and ov.custom_window is None
                for ov in todays_overrides
            )
            if has_full_day_blackout:
                current_date += timedelta(days=1)
                continue

            # collect custom working hours for today
            positive_overrides = [
                ov.custom_window
                for ov in todays_overrides
                if ov.is_available and ov.custom_window is not None
            ]

            # use custom hours if provided, otherwise follow the weekly rules
            if positive_overrides:
                daily_windows = positive_overrides
            else:  # follow weekly work hours
                pg_dow = (current_date.weekday() + 1) % 7

                daily_windows = []
                for rule in rules_by_dow[pg_dow]:
                    if current_date < rule.valid_from:
                        continue
                    if rule.valid_until is not None and current_date > rule.valid_until:
                        continue

                    # combine todays calendar date with the rule's clock time
                    # convert to utc through TimeWindow so all ranges use the same timezone
                    tz = ZoneInfo(rule.timezone)
                    local_start = datetime.combine(
                        current_date, rule.start_time, tzinfo=tz
                    )
                    local_end = datetime.combine(current_date, rule.end_time, tzinfo=tz)
                    daily_windows.append(TimeWindow(local_start, local_end))

            # collect parts of the day that the advisor has blocked
            partial_blackouts = [
                ov.custom_window
                for ov in todays_overrides
                if not ov.is_available and ov.custom_window is not None
            ]

            # remove blocked times from each working window
            for win in daily_windows:
                working_windows.extend(win.subtract_many(partial_blackouts))

            current_date += timedelta(days=1)

        return working_windows

    @classmethod
    def compute_available_slots(
        cls,
        *,
        rules: list[AvailabilityRule],
        overrides: list[AvailabilityOverride],
        busy_windows: list[TimeWindow],
        meeting_type: MeetingType,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> list[BookableSlot]:
        """
        Computes exact bookable slots in UTC across [start_date, end_date].
        Guarantees:
          1. slot_window falls completely inside an active working_window.
          2. reserved_window (slot + before/after buffers) does NOT overlap any busy_window.
          3. slot_window.start_at respects minimum_notice_minutes and max_days_in_advance.
        """
        working_windows = cls.resolve_working_windows(
            rules=rules,
            overrides=overrides,
            start_date=start_date,
            end_date=end_date,
        )

        duration_delta = timedelta(minutes=meeting_type.duration_minutes)
        step_delta = timedelta(minutes=meeting_type.slot_interval_minutes)
        earliest_allowed = now + timedelta(minutes=meeting_type.minimum_notice_minutes)
        latest_allowed = now + timedelta(days=meeting_type.max_days_in_advance)

        # sort blocks so we can short-circuit overlap checks
        sorted_busy = sorted(busy_windows, key=lambda b: b.start_at)
        slots: list[BookableSlot] = []

        for work_win in working_windows:
            cursor = work_win.start_at

            # keep generating slots while the full meeting still fits
            while cursor + duration_delta <= work_win.end_at:
                if earliest_allowed <= cursor <= latest_allowed:
                    candidate_slot = TimeWindow(cursor, cursor + duration_delta)
                    candidate_reserved = meeting_type.buffers.expand(candidate_slot)

                    # check if slot bumps into any busy meeting
                    has_conflict = any(
                        candidate_reserved.overlaps(busy)
                        for busy in sorted_busy
                        if busy.end_at > candidate_reserved.start_at
                        and busy.start_at < candidate_reserved.end_at
                    )

                    if not has_conflict:
                        slots.append(
                            BookableSlot(
                                slot_window=candidate_slot,
                                reserved_window=candidate_reserved,
                            )
                        )
                cursor += step_delta

        return slots

    @classmethod
    def compute_monthly_summary(
        cls,
        *,
        rules: list[AvailabilityRule],
        overrides: list[AvailabilityOverride],
        busy_windows: list[TimeWindow],
        meeting_type: MeetingType,
        year: int,
        month: int,
        viewer_timezone: str,
        now: datetime,
    ) -> list[DailyAvailabilitySummary]:
        """
        group available slots by date in the advisor's timezone
        return the slot count, earliest start and full slot list for each day
        """

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        bookable_slots = cls.compute_available_slots(
            rules=rules,
            overrides=overrides,
            busy_windows=busy_windows,
            meeting_type=meeting_type,
            start_date=first_day - timedelta(days=1),
            end_date=last_day + timedelta(days=1),
            now=now,
        )

        # convert slot times into the timezone used by the calendar viewer
        viewer_tz = ZoneInfo(viewer_timezone)
        slots_by_date: dict[date, list[BookableSlot]] = defaultdict(list)

        # group slots under their local calendar date
        for slot in bookable_slots:
            local_date = slot.start_at.astimezone(viewer_tz).date()
            if first_day <= local_date <= last_day:
                slots_by_date[local_date].append(slot)

        result: list[DailyAvailabilitySummary] = []
        day = first_day

        # build a summary for every day, even if no slots are available
        while day <= last_day:
            day_slots = tuple(slots_by_date.get(day, []))
            result.append(
                DailyAvailabilitySummary(
                    calendar_date=day,
                    total_available_slots=len(day_slots),
                    earliest_slot_start=day_slots[0].start_at if day_slots else None,
                    slots=day_slots,
                )
            )
            day += timedelta(days=1)

        return result
