import { useEffect, useRef } from 'react'
import { FiCalendar, FiCheck, FiClock, FiMail, FiUser } from 'react-icons/fi'

function BookingConfirmationModal({
  meetingName,
  duration,
  formattedDate,
  selectedTime,
  advisorName,
  email,
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
        </div>

        <div className="confirmation-email">
          <FiMail />
          <p>
            A confirmation email has been sent to <strong>{email}</strong>. It includes your
            calendar invite and meeting link.
          </p>
        </div>

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
