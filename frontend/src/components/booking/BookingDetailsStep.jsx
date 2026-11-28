import { useState } from 'react'
import {
  FiArrowLeft,
  FiArrowRight,
  FiCalendar,
  FiClock,
  FiEdit2,
  FiShield,
  FiUser,
} from 'react-icons/fi'
import { bookMeeting, toBookingStart } from '../../services/BookingApi'
import BookingConfirmationModal from './BookingConfirmationModal'

function BookingDetailsStep({
  selectedType,
  meetingName,
  duration = 45,
  selectedDate,
  selectedTime,
  advisor,
  onBack,
  onChangeBooking,
  onBookingComplete,
}) {
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [meetingUri, setMeetingUri] = useState(null)
  const [rescheduleUrl, setRescheduleUrl] = useState(null)
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    notes: '',
  })

  const handleChange = (event) => {
    const { name, value } = event.target

    setFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }))
  }

  const consultationName =
    meetingName ??
    (selectedType === 'follow-up' ? 'Follow-up Consultation' : 'Introduction Meeting')

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (isSubmitting) {
      return
    }

    setSubmitError(null)
    setIsSubmitting(true)

    try {
      const notes = formData.notes.trim()
      const result = await bookMeeting(advisor.id, {
        name: `${formData.firstName.trim()} ${formData.lastName.trim()}`,
        email: formData.email.trim(),
        phone_number: formData.phone.trim(),
        title: consultationName,
        start: toBookingStart(selectedDate, selectedTime),
        duration_minutes: duration,
        ...(notes && { notes }),
      })

      setMeetingUri(result.meeting_uri ?? null)
      setRescheduleUrl(result.reschedule_url ?? null)
      setIsConfirmed(true)
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const formattedDate = selectedDate
    ? selectedDate.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : ''

  return (
    <div className="booking-details-content">
      <div className="booking-summary">
        <div className="summary-item">
          <FiClock />

          <div>
            <span>CONSULTATION</span>
            <p>
              {consultationName} ({duration} min)
            </p>
          </div>
        </div>

        <div className="summary-item">
          <FiCalendar />

          <div>
            <span>SELECTED SLOT</span>
            <p>
              {formattedDate} at {selectedTime}
            </p>
          </div>
        </div>

        <div className="summary-item">
          <FiUser />

          <div>
            <span>ADVISOR</span>
            <p>{advisor.username}</p>
          </div>
        </div>

        <button type="button" className="change-booking-button" onClick={onChangeBooking}>
          Change
          <FiEdit2 />
        </button>
      </div>

      <form className="booking-details-form" onSubmit={handleSubmit}>
        <div className="details-heading">
          <div>
            <h2>Your Contact Details</h2>

            <p>Enter your information to receive secure meeting access credentials.</p>
          </div>

          <span>STEP 4 OF 4</span>
        </div>

        <div className="details-form-grid">
          <div className="form-group">
            <label htmlFor="firstName">
              First Name <span>*</span>
            </label>

            <input
              id="firstName"
              name="firstName"
              type="text"
              placeholder="e.g. Daniel"
              value={formData.firstName}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="lastName">
              Last Name <span>*</span>
            </label>

            <input
              id="lastName"
              name="lastName"
              type="text"
              placeholder="e.g. Foster"
              value={formData.lastName}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">
              Email Address <span>*</span>
            </label>

            <input
              id="email"
              name="email"
              type="email"
              placeholder="e.g. daniel.foster@domain.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="phone">
              Phone Number <span>*</span>
            </label>

            <input
              id="phone"
              name="phone"
              type="tel"
              placeholder="e.g. +1 (503) 555-0167"
              value={formData.phone}
              onChange={handleChange}
              maxLength={32}
              required
            />
          </div>

          <div className="form-group full-width">
            <label htmlFor="notes">
              Anything you'd like the advisor to know? <em>(Optional)</em>
            </label>

            <textarea
              id="notes"
              name="notes"
              placeholder="Share topics, questions, or specific accounts you want to cover..."
              value={formData.notes}
              onChange={handleChange}
              maxLength={2000}
            />
          </div>
        </div>

        <div className="security-notice">
          <FiShield />

          <p>
            <strong>SEC Rule 204-2 & Zero-Knowledge Encryption compliant.</strong> Your contact
            details remain strictly confidential and are never shared or sold to third parties.
          </p>
        </div>

        {submitError && (
          <p className="booking-error" role="alert">
            {submitError}
          </p>
        )}

        <div className="details-actions">
          <button type="button" className="back-button" onClick={onBack}>
            <FiArrowLeft />
            Back to Date & Time
          </button>

          <button type="submit" className="confirm-booking-button" disabled={isSubmitting}>
            {isSubmitting ? 'Scheduling...' : 'Confirm & Schedule Meeting'}
            <FiArrowRight />
          </button>
        </div>
      </form>
      {isConfirmed && (
        <BookingConfirmationModal
          meetingName={consultationName}
          duration={duration}
          formattedDate={formattedDate}
          selectedTime={selectedTime}
          advisorName={advisor.username}
          email={formData.email}
          meetingUri={meetingUri}
          rescheduleUrl={rescheduleUrl}
          onDone={() => {
            setIsConfirmed(false)
            onBookingComplete?.()
          }}
        />
      )}
    </div>
  )
}

export default BookingDetailsStep
