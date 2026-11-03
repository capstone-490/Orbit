// Substantial AI assistance used; verified with frontend tests and production build.
import { useEffect, useState } from "react";
import { DayPicker } from "@daypicker/react";
import "@daypicker/react/style.css";

import {FiArrowLeft, FiArrowRight, FiCheck, FiClock, FiZap,} from "react-icons/fi";

import { getAvailableTimes } from "../../services/BookingApi";

function DateTimeStep({
  selectedDate,
  setSelectedDate,
  selectedTime,
  setSelectedTime,
  onBack,
  onContinue,
}) {
  const [availableTimes, setAvailableTimes] = useState([]);
  const [loadingTimes, setLoadingTimes] = useState(false);

  useEffect(() => {
    if (!selectedDate) {
      setAvailableTimes([]);
      return;
    }

    const loadAvailableTimes = async () => {
      setLoadingTimes(true);
      setSelectedTime(null);

      try {
        const times = await getAvailableTimes(selectedDate);
        setAvailableTimes(times);
      } catch (error) {
        console.error("Failed to load available times:", error);
        setAvailableTimes([]);
      } finally {
        setLoadingTimes(false);
      }
    };

    loadAvailableTimes();
  }, [selectedDate, setSelectedTime]);

  return (
    <div className="date-time-content">
      <div className="date-time-heading">
        <h2>Select Date & Time</h2>

        <p>
          <span className="meeting-dot"></span>
          Introduction Meeting · 45 min consultation
        </p>
      </div>

      <div className="date-time-grid">
        <div className="calendar-card">
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={setSelectedDate}
            disabled={{ before: new Date() }}
            startMonth={new Date()}
          />

          <div className="timezone-row">
            <div>
              <FiClock />
              <span>Time zone</span>
            </div>

            <span>Eastern Time</span>
          </div>
        </div>

        <div className="time-card">
          <div className="time-card-header">
            <strong>
              {selectedDate
                ? selectedDate.toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })
                : "Select a date"}
            </strong>

            {selectedDate && !loadingTimes && (
              <span>
                {availableTimes.length} slots free
              </span>
            )}
          </div>

          {!selectedDate && (
            <p>Select a date to see available times.</p>
          )}

          {loadingTimes && (
            <p>Loading available times...</p>
          )}

          {selectedDate && !loadingTimes && (
            <>
              <p>Select your preferred start time:</p>

              <div className="time-slots">
                {availableTimes.map((time) => (
                  <button
                    key={time}
                    type="button"
                    className={
                      selectedTime === time
                        ? "selected"
                        : ""
                    }
                    onClick={() =>
                      setSelectedTime(time)
                    }
                  >
                    {time}

                    {selectedTime === time && (
                      <FiCheck />
                    )}
                  </button>
                ))}
              </div>

              <div className="booking-notice">
                <FiZap />

                <span>
                  Calendar invite will be sent after
                  booking confirmation.
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="date-time-actions">
        <button
          type="button"
          className="back-button"
          onClick={onBack}
        >
          <FiArrowLeft />
          Back to Session Type
        </button>

        <button
          type="button"
          className="continue-button"
          disabled={!selectedDate || !selectedTime}
          onClick={onContinue}
        >
          Continue to Details
          <FiArrowRight />
        </button>
      </div>
    </div>
  );
}

export default DateTimeStep;