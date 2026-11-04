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

function BookingDetailsStep({
  selectedType,
  selectedDate,
  selectedTime,
  advisor,
  onBack,
  onChangeBooking,
}) {
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

  const handleSubmit = (event) => {
    event.preventDefault()
  }

  const formattedDate = selectedDate
    ? selectedDate.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : ''

  const meetingName =
    selectedType === 'follow-up' ? 'Follow-up Consultation' : 'Introduction Meeting'

  return (
    <div className="booking-details-content">
      <div className="booking-summary">
        <div className="summary-item">
          <FiClock />

          <div>
            <span>CONSULTATION</span>
            <p>{meetingName} (45 min)</p>
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
            <p>
              {' '}
              {advisor.firstName} {advisor.lastName}
              {advisor.designation && `, ${advisor.designation}`}
            </p>
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

          <span>STEP 3 OF 3</span>
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
              Phone Number <em>(Optional)</em>
            </label>

            <input
              id="phone"
              name="phone"
              type="tel"
              placeholder="e.g. +1 (503) 555-0167"
              value={formData.phone}
              onChange={handleChange}
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

        <div className="details-actions">
          <button type="button" className="back-button" onClick={onBack}>
            <FiArrowLeft />
            Back to Date & Time
          </button>

          <button type="submit" className="confirm-booking-button">
            Confirm & Schedule Meeting
            <FiArrowRight />
          </button>
        </div>
      </form>
    </div>
  )
}

export default BookingDetailsStep
