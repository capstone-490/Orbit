//Above 50% AI generated

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SESSION_TYPES } from "../constants/sessionTypes";
import "../styles/Calendar.css";
import { calendarApi } from "../services/CalendarApi";
import { getCurrentAdvisor } from "../services/AuthApi";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

// Calendar layout configuration
const DAY_START_HOUR = 0;
const DAY_END_HOUR = 24;
const PIXELS_PER_HOUR = 64;
const PIXELS_PER_MIN = PIXELS_PER_HOUR / 60;

// TODO: https://orbit.ca/book-meeting/<advisorId> once the backend exposes the current advisor's id
const BOOKING_URL = "http://localhost:5173/book-meeting";

const BUSY_EVENT_STYLE = {
  label: "Busy",
  bg: "#EEF0F4",
  bd: "#C9CED8",
  fg: "#414B5D",
  dot: "#697589",
};

const DEFAULT_SESSION_STYLE = {
  label: "Meeting",
  bg: "#EEF0F4",
  bd: "#C9CED8",
  fg: "#414B5D",
  dot: "#697589",
};

// Date utility functions
const addDays = (date, amount) => {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
};

const addMonths = (date, amount) => {
  const result = new Date(date.getFullYear(), date.getMonth() + amount, 1);

  const lastDayOfMonth = new Date(
    result.getFullYear(),
    result.getMonth() + 1,
    0,
  ).getDate();

  result.setDate(Math.min(date.getDate(), lastDayOfMonth));
  return result;
};

const startOfDay = (date) =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate());

const startOfWeek = (date) => addDays(startOfDay(date), -date.getDay());

const isSameDay = (firstDate, secondDate) =>
  firstDate.toDateString() === secondDate.toDateString();

const getDayKey = (date) =>
  `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;

const formatTime = (date) =>
  date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

const formatDate = (date, options) => date.toLocaleDateString([], options);

const getMinutesSinceMidnight = (date) =>
  date.getHours() * 60 + date.getMinutes();

const formatDuration = (totalMinutes) => {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return (
    [hours && `${hours}h`, minutes && `${minutes}m`]
      .filter(Boolean)
      .join(" ") || "0m"
  );
};

// Returns the styling configuration for an appointment type
const typeOf = (appointment) =>
  SESSION_TYPES[appointment.typeId] ?? DEFAULT_SESSION_STYLE;

// Returns the appointment's display name
const labelOf = (appointment) =>
  SESSION_TYPES[appointment.typeId]?.label ?? (appointment.title || "Meeting");

// Returns the appropriate styling for busy events or sessions
const styleOf = (appointment) =>
  appointment.kind === "busy" ? BUSY_EVENT_STYLE : typeOf(appointment);

// Determines which dates should be displayed for each calendar view
function getCalendarRange(view, selectedDate) {
  if (view === "month") {
    const firstday = new Date(
      selectedDate.getFullYear(),
      selectedDate.getMonth(),
      1,
    );
    const lastDay = new Date(
      selectedDate.getFullYear(),
      selectedDate.getMonth() + 1,
      0,
    );
    return {
      start: startOfWeek(firstday),
      end: addDays(startOfWeek(lastDay), 7),
    };
  }
  if (view === "week") {
    const weekStart = startOfWeek(selectedDate);
    return {
      start: weekStart,
      end: addDays(weekStart, 7),
    };
  }
  const dayStart = startOfDay(selectedDate);
  return {
    start: dayStart,
    end: addDays(dayStart, 1),
  };
}

// Heading displayed above the calendar
function getCalendarTitle(view, selectedDate) {
  if (view === "month")
    return formatDate(selectedDate, {
      month: "long",
      year: "numeric",
    });
  if (view === "day")
    return formatDate(selectedDate, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  const weekStart = startOfWeek(selectedDate);
  const weekEnd = addDays(weekStart, 6);

  return `${formatDate(weekStart, {
    month: "short",
    day: "numeric",
  })} – ${formatDate(weekEnd, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })}`;
}

const UPCOMING_WINDOW_DAYS = 30;

function useRefreshTrigger() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const refresh = useCallback(() => setRefreshTrigger((p) => p + 1), []);
  useEffect(() => {
    window.addEventListener("focus", refresh);
    const refreshInterval = setInterval(refresh, 60000);
    return () => {
      window.removeEventListener("focus", refresh);
      clearInterval(refreshInterval);
    };
  }, [refresh]);
  return [refreshTrigger, refresh];
}

// Fetches appointments for the currently selected calendar range
function useAppointments(view, selectedDate, advisorId, refreshTrigger) {
  const { start, end } = useMemo(
    () => getCalendarRange(view, selectedDate),
    [view, selectedDate],
  );
  const [appointmentState, setAppointmentState] = useState({
    data: [],
    loading: true,
    error: null,
  });
  const previousRangeKey = useRef(null);

  useEffect(() => {
    if (advisorId == null) return;
    const abortController = new AbortController();
    const currentRangeKey = `${start.getTime()}-${end.getTime()}`;

    // Keep existing appointments visible when refreshing the same date range
    const isBackgroundRefresh = previousRangeKey.current === currentRangeKey;

    if (!isBackgroundRefresh) {
      setAppointmentState({
        data: [],
        loading: true,
        error: null,
      });
    }

    calendarApi
      .getAppointments(start, end, {
        signal: abortController.signal,
        advisorId,
      })
      .then((appointments) => {
        previousRangeKey.current = currentRangeKey;
        setAppointmentState({
          data: appointments,
          loading: false,
          error: null,
        });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;

        setAppointmentState((previousState) => ({
          ...previousState,
          loading: false,
          error,
        }));
      });
    return () => abortController.abort();
  }, [start.getTime(), end.getTime(), refreshTrigger, advisorId]);

  return appointmentState;
}
function useCalendarSummary(advisorId, refreshTrigger) {
  const [summary, setSummary] = useState({
    bookedThisMonth: null,
    upcoming: null, // null = not loaded yet
  });

  useEffect(() => {
    if (advisorId == null) return;
    // Recomputed on every refresh so month rollover and "now" stay current
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const nextMonthStart = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const upcomingEnd = addDays(startOfDay(now), UPCOMING_WINDOW_DAYS + 1);
    const rangeEnd =
      upcomingEnd > nextMonthStart ? upcomingEnd : nextMonthStart;

    const abortController = new AbortController();
    calendarApi
      .getAppointments(monthStart, rangeEnd, {
        signal: abortController.signal,
        advisorId,
      })
      .then((appointments) => {
        const sessions = appointments.filter(
          (appointment) => appointment.kind === "session",
        );
        setSummary({
          bookedThisMonth: sessions.filter(
            (appointment) => appointment.start < nextMonthStart,
          ).length,
          upcoming: sessions
            .filter((appointment) => appointment.start >= now)
            .sort((first, second) => first.start - second.start)
            .slice(0, 4),
        });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        // Keep the last good values on a failed background refresh
        setSummary((previous) => ({
          bookedThisMonth: previous.bookedThisMonth,
          upcoming: previous.upcoming ?? [],
        }));
      });
    return () => abortController.abort();
  }, [advisorId, refreshTrigger]);

  return summary;
}
// Displays the calendar as a monthly grid
function MonthView({ date, appts, loading, onPickDay }) {
  const { start, end } = getCalendarRange("month", date);

  const numberOfWeeks = Math.round((end - start) / 864e5 / 7);
  const calendarDays = Array.from({ length: numberOfWeeks * 7 }, (_, index) =>
    addDays(start, index),
  );

  // Organize appointments by their calendar date
  const appointmentsByDay = useMemo(() => {
    const groupedAppointments = new Map();
    appts.forEach((appointment) => {
      const dateKey = getDayKey(appointment.start);
      const existingAppointments = groupedAppointments.get(dateKey) || [];
      groupedAppointments.set(
        dateKey,
        [...existingAppointments, appointment].sort(
          (first, second) => first.start - second.start,
        ),
      );
    });
    return groupedAppointments;
  }, [appts]);
  return (
    <div className="grid7" role="grid">
      {["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"].map((dayName) => (
        <div key={dayName} className="dow">
          {dayName}
        </div>
      ))}
      {calendarDays.map((calendarDate) => {
        const dayAppointments =
          appointmentsByDay.get(getDayKey(calendarDate)) || [];
        const isOutsideCurrentMonth =
          calendarDate.getMonth() !== date.getMonth();
        return (
          <div
            key={getDayKey(calendarDate)}
            className={`cell ${isOutsideCurrentMonth ? "out" : ""} ${calendarDate.getDay() % 6 === 0 ? "wknd" : ""}`}
            onClick={() => onPickDay(calendarDate)}
          >
            <span
              className={`num ${isSameDay(calendarDate, new Date()) ? "today" : ""}`}
            >
              {calendarDate.getDate()}
            </span>
            {loading &&
              !isOutsideCurrentMonth &&
              calendarDate.getDate() % 3 === 0 && <div className="skel" />}
            {dayAppointments.slice(0, 2).map((appointment) => {
              const style = styleOf(appointment);
              const appointmentLabel =
                appointment.kind === "busy" ? "Busy" : appointment.client;
              return (
                <div
                  key={appointment.id}
                  className="chip"
                  style={{
                    background: style.bg,
                    borderColor: style.bd,
                    color: style.fg,
                  }}
                  title={`${formatTime(appointment.start)} ${appointmentLabel}`}
                >
                  <i style={{ background: style.dot }} />
                  {formatTime(appointment.start)} {appointmentLabel}
                </div>
              );
            })}
            {dayAppointments.length > 2 && (
              <div className="more">+{dayAppointments.length - 2} more</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Assigns overlapping appointments to separate columns
function layoutAppointments(appointments) {
  const sortedAppointments = [...appointments].sort(
    (first, second) => first.start - second.start,
  );
  const positionedAppointments = [];
  let currentGroup = [],
    currentGroupEnd = 0;

  // Finalizes a group and assigns its total column count
  const finalizeGroup = () => {
    const columnCount = Math.max(
      1,
      ...currentGroup.map((item) => item.column + 1),
    );
    currentGroup.forEach((item) =>
      positionedAppointments.push({ ...item, columnCount }),
    );
    currentGroup = [];
  };
  sortedAppointments.forEach((appointment) => {
    const startMinutes = getMinutesSinceMidnight(appointment.start);
    const endMinutes = startMinutes + appointment.minutes;

    // Start a new group when the previous appointments no longer overlap
    if (currentGroup.length > 0 && startMinutes >= currentGroupEnd) {
      finalizeGroup();
    }
    const occupiedColumns = currentGroup
      .filter((item) => item.endMinutes > startMinutes)
      .map((item) => item.column);
    let availableColumn = 0;
    while (occupiedColumns.includes(availableColumn)) availableColumn++;
    currentGroup.push({
      appointment,
      startMinutes,
      endMinutes,
      column: availableColumn,
    });
    currentGroupEnd = Math.max(currentGroupEnd, endMinutes);
  });
  finalizeGroup();
  return positionedAppointments;
}

// Displays appointments along a vertical hourly timeline
function TimeGrid({ days, appts, isDay }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  useEffect(() => {
    const clockInterval = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(clockInterval);
  }, []);
  const visibleHours = Array.from(
    { length: DAY_END_HOUR - DAY_START_HOUR },
    (_, index) => DAY_START_HOUR + index,
  );
  const currentTimePosition =
    (getMinutesSinceMidnight(currentTime) - DAY_START_HOUR * 60) *
    PIXELS_PER_MIN;
  const isCurrentTimeVisible =
    currentTimePosition >= 0 &&
    currentTimePosition <= (DAY_END_HOUR - DAY_START_HOUR) * PIXELS_PER_HOUR;
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 8 * PIXELS_PER_HOUR;
  }, []);
  return (
    <div className="tg-scroll" ref={scrollRef}>
      <div
        className="tg"
        style={{
          gridTemplateColumns: `56px repeat(${days.length}, minmax(${isDay ? 200 : 110}px, 1fr))`,
        }}
      >
        {!isDay && <div className="tg-head" />}
        {!isDay &&
          days.map((calendarDate) => (
            <div key={getDayKey(calendarDate)} className="tg-head">
              <span
                className={isSameDay(calendarDate, currentTime) ? "today" : ""}
              >
                {formatDate(calendarDate, { weekday: "short" })}{" "}
                {calendarDate.getDate()}
              </span>
            </div>
          ))}
        <div className="gutter">
          {visibleHours.map((hour) => (
            <span key={hour} style={{ height: PIXELS_PER_HOUR }}>
              {hour % 12 || 12} {hour < 12 ? "AM" : "PM"}
            </span>
          ))}
        </div>
        {days.map((calendarDate) => {
          const dayAppointments = layoutAppointments(
            appts.filter((appointment) =>
              isSameDay(appointment.start, calendarDate),
            ),
          );
          return (
            <div
              key={getDayKey(calendarDate)}
              className="col"
              style={{ height: visibleHours.length * PIXELS_PER_HOUR }}
            >
              {dayAppointments.map(
                ({ appointment, startMinutes, column, columnCount }) => {
                  const style = styleOf(appointment);
                  return (
                    <div
                      key={appointment.id}
                      className="ev"
                      style={{
                        top:
                          (startMinutes - DAY_START_HOUR * 60) * PIXELS_PER_MIN,
                        height: appointment.minutes * PIXELS_PER_MIN - 2,
                        left: `${(column / columnCount) * 100}%`,
                        width: `calc(${100 / columnCount}% - 4px)`,
                        background: style.bg,
                        borderColor: style.dot,
                        color: style.fg,
                      }}
                    >
                      <b>
                        {appointment.kind === "busy"
                          ? "Busy"
                          : appointment.client}
                      </b>
                      <span>
                        {formatTime(appointment.start)}
                        {appointment.kind === "session" &&
                          ` · ${labelOf(appointment)}`}
                      </span>
                      {isDay && appointment.meetUrl && (
                        <a
                          href={appointment.meetUrl}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Join Meet
                        </a>
                      )}
                    </div>
                  );
                },
              )}
              {isSameDay(calendarDate, currentTime) && isCurrentTimeVisible && (
                <div className="now" style={{ top: currentTimePosition }}>
                  {isDay && <em>NOW</em>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Main calendar page
export default function Calendar() {
  const [view, setView] = useState("month");
  const [selectedDate, setSelectedDate] = useState(() => new Date()); // single source of truth for all views
  const [advisorId, setAdvisorId] = useState(USE_MOCK ? 1 : null);
  useEffect(() => {
    if (USE_MOCK) return;
    getCurrentAdvisor()
      .then((advisor) => setAdvisorId(advisor.id))
      .catch(() => setAdvisorId(null));
  }, []);

  const [refreshTrigger, retry] = useRefreshTrigger();
  const {
    data: appointments,
    loading,
    error,
  } = useAppointments(view, selectedDate, advisorId, refreshTrigger);
  const { bookedThisMonth: monthlyBookingCount, upcoming } = useCalendarSummary(
    advisorId,
    refreshTrigger,
  );
  const upcomingSessions = upcoming ?? [];

  // Calculate session statistics for the currently loaded range

  const sessionStats = useMemo(() => {
    const sessions = appointments.filter(
      (appointment) => appointment.kind === "session",
    );
    return {
      count: sessions.length,
      totalMinutes: sessions.reduce(
        (total, appointment) => total + appointment.minutes,
        0,
      ),
    };
  }, [appointments]);

  // Check whether the Google Calendar account is connected
  const [googleStatus, setGoogleStatus] = useState(null);
  useEffect(() => {
    calendarApi
      .getGoogleStatus()
      .then(setGoogleStatus)
      .catch(() => setGoogleStatus(null));
  }, []);
  const needsGoogleReconnect =
    error?.status === 401 ||
    error?.status === 409 ||
    (googleStatus && !googleStatus.connected);

  const [copyStatus, setCopyStatus] = useState("idle");
  const copyResetTimer = useRef(null);
  useEffect(() => () => clearTimeout(copyResetTimer.current), []);

  const copyBookingLink = () => {
    const showStatus = (status) => {
      setCopyStatus(status);
      clearTimeout(copyResetTimer.current);
      copyResetTimer.current = setTimeout(() => setCopyStatus("idle"), 2000);
    };
    if (!navigator.clipboard?.writeText) {
      showStatus("failed");
      return;
    }
    navigator.clipboard
      .writeText(BOOKING_URL)
      .then(() => showStatus("copied"))
      .catch((error) => {
        console.error("Failed to copy booking link", error);
        showStatus("failed");
      });
  };
  // Navigate between months, weeks, and individual days
  const navigateCalendar = (direction) =>
    setSelectedDate((currentDate) =>
      view === "month"
        ? addMonths(currentDate, direction)
        : addDays(currentDate, direction * (view === "week" ? 7 : 1)),
    );

  // Switch to the daily calendar when a date is selected
  const handleDaySelection = (date) => {
    setSelectedDate(date);
    setView("day");
  };

  return (
    <div className="cal-page">
      <header className="top">
        <div>
          <h1>Calendar</h1>
          <p>
            Your meetings, educational sessions, and one public booking link for
            clients.
          </p>
        </div>
        <div className="actions">
          <button className="btn" onClick={copyBookingLink} aria-live="polite">
            {copyStatus === "copied"
              ? "Copied!"
              : copyStatus === "failed"
                ? "Couldn't copy"
                : "Copy booking link"}
          </button>
          <button className="btn primary">+ New meeting</button>
        </div>
      </header>

      <div className="card link">
        <div>
          <small>PUBLIC BOOKING LINK</small>{" "}
          <a href={BOOKING_URL}>orbit.ca/book-meeting</a>
          <p>
            Clients can book portfolio reviews, planning sessions, and quick
            check-ins directly.
          </p>
        </div>
        <span className="pill">
          {" "}
          {Object.keys(SESSION_TYPES).length} Session types{" "}
          {monthlyBookingCount !== null &&
            ` · ${monthlyBookingCount} Booked this month`}
        </span>
      </div>

      <div className="card toolbar">
        <div className="nav">
          <button aria-label="Previous" onClick={() => navigateCalendar(-1)}>
            ‹
          </button>
          {<h2>{getCalendarTitle(view, selectedDate)}</h2>}
          <button aria-label="Next" onClick={() => navigateCalendar(1)}>
            ›
          </button>
          <button
            className="today-btn"
            onClick={() => setSelectedDate(new Date())}
          >
            Today
          </button>
        </div>
        <div className="seg" role="tablist">
          {["month", "week", "day"].map((calendarView) => (
            <button
              key={calendarView}
              role="tab"
              aria-selected={view === calendarView}
              className={view === calendarView ? "on" : ""}
              onClick={() => setView(calendarView)}
            >
              {calendarView[0].toUpperCase() + calendarView.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="layout">
        <div className="card cal">
          {needsGoogleReconnect && (
            <div className="banner">
              Connect Google Calendar to see your events.{" "}
              <button
                onClick={() => {
                  window.location.href = calendarApi.connectUrl;
                }}
              >
                Connect
              </button>
            </div>
          )}
          {error && error.status !== 401 && error.status !== 409 && (
            <div className="banner">
              Couldn't load appointments. <button onClick={retry}>Retry</button>
            </div>
          )}{" "}
          {view === "day" && (
            <div className="day-head">
              <div className="day-title">
                <div className="day-badge">
                  <small>
                    {formatDate(selectedDate, {
                      weekday: "short",
                    }).toUpperCase()}
                  </small>
                  <b>{selectedDate.getDate()}</b>
                </div>
                <div>
                  <h2>
                    {formatDate(selectedDate, {
                      weekday: "long",
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </h2>
                  <p>
                    {loading
                      ? "Loading..."
                      : sessionStats.count === 0
                        ? "No scheduled appointments"
                        : `${sessionStats.count} scheduled appointment${sessionStats.count === 1 ? "" : "s"} · ${formatDuration(sessionStats.totalMinutes)} meeting time`}
                  </p>
                </div>
              </div>
            </div>
          )}
          {view === "month" && (
            <MonthView
              date={selectedDate}
              appts={appointments}
              loading={loading}
              onPickDay={handleDaySelection}
            />
          )}
          {view === "week" && (
            <TimeGrid
              days={Array.from({ length: 7 }, (_, index) =>
                addDays(startOfWeek(selectedDate), index),
              )}
              appts={appointments}
            />
          )}
          {view === "day" && (
            <TimeGrid
              days={[startOfDay(selectedDate)]}
              appts={appointments}
              isDay
            />
          )}
          {loading && view !== "day" && (
            <div className="loading">Loading...</div>
          )}
        </div>

        <aside>
          <div className="card side">
            <h3>
              Upcoming{" "}
              <span className="pill">
                {" "}
                {upcomingSessions.length}{" "}
                {upcomingSessions.length === 1 ? "SESSION" : "SESSIONS"}
              </span>
            </h3>
            {upcoming === null && <p className="muted">Loading...</p>}
            {upcoming !== null && upcomingSessions.length === 0 && (
              <p className="muted">Nothing scheduled.</p>
            )}
            {upcomingSessions.map((appointment) => {
              const style = typeOf(appointment);
              return (
                <div
                  key={appointment.id}
                  className="up"
                  style={{ background: style.bg, borderLeftColor: style.dot }}
                >
                  <div>
                    <b>{labelOf(appointment)}</b>
                  </div>
                  <div>{appointment.client}</div>
                  <small style={{ color: style.fg }}>
                    {formatDate(appointment.start, {
                      weekday: "short",
                      day: "numeric",
                    })}{" "}
                    · {formatTime(appointment.start)} · {appointment.minutes}m
                  </small>
                  {appointment.meetUrl && (
                    <a
                      className="meet-btn"
                      href={appointment.meetUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: style.fg, borderColor: style.bd }}
                    >
                      Join Meet
                    </a>
                  )}
                </div>
              );
            })}
          </div>
          <div className="card side">
            <h3>Session types</h3>
            {Object.values(SESSION_TYPES).map((sessionType) => (
              <div
                key={sessionType.label}
                className="st"
                style={{
                  background: sessionType.bg,
                  borderColor: sessionType.bd,
                }}
              >
                <div>
                  <b style={{ color: sessionType.fg }}>
                    <i style={{ background: sessionType.dot }} />
                    {sessionType.label}
                  </b>
                  <span className="tag" style={{ color: sessionType.fg }}>
                    {sessionType.minutes} min
                  </span>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
