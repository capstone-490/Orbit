import { useEffect, useRef } from 'react'
import { FiCalendar, FiCheck, FiClock, FiMail, FiUser, FiVideo } from 'react-icons/fi'

function BookingConfirmationModal({
  meetingName,
  duration,
  formattedDate,
  selectedTime,
  advisorName,
  email,
  meetingUri,
  rescheduleUrl,
  onDone,
}) {
  const doneButtonRef = useRef(null)

  // Put keyboard focus on the button and let Escape close the pop-up
  useEffect(() => {
    doneButtonRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onDone()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onDone])

  return (
    <div className="confirmation-overlay">
      <div
        className="confirmation-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-title"
      >
        <div className="confirmation-icon">
          <FiCheck />
        </div>

        <h2 id="confirmation-title">Meeting Scheduled!</h2>

        <p className="confirmation-subtitle">
          Your {meetingName} with {advisorName} is confirmed.
        </p>

        <div className="confirmation-details">
          <div className="confirmation-row">
            <FiClock />
            <span>Consultation</span>
            <strong>
              {meetingName} ({duration} min)
            </strong>
          </div>

          <div className="confirmation-row">
            <FiCalendar />
            <span>Date & Time</span>
            <strong>
              {formattedDate} at {selectedTime}
            </strong>
          </div>

          <div className="confirmation-row">
            <FiUser />
            <span>Advisor</span>
            <strong>{advisorName}</strong>
          </div>

          {meetingUri && (
            <div className="confirmation-row">
              <FiVideo />
              <span>Google Meet</span>
              <strong>
                <a href={meetingUri} target="_blank" rel="noopener noreferrer">
                  {meetingUri.replace(/^https?:\/\//, '')}
                </a>
              </strong>
            </div>
          )}
        </div>

        <div className="confirmation-email">
          <FiMail />
          <p>
            A Google Calendar invite and reschedule link have been sent to <strong>{email}</strong>.
            The invite includes the meeting link.
          </p>
        </div>

        {rescheduleUrl && (
          <p>
            Need a different time? <a href={rescheduleUrl}>Reschedule this meeting</a>
          </p>
        )}

        <button
          ref={doneButtonRef}
          type="button"
          className="confirmation-done-button"
          onClick={onDone}
        >
          Done
        </button>
      </div>
    </div>
  )
}

export default BookingConfirmationModal
