// Substantial AI assistance used; verified with frontend tests and production build.

import { useState } from 'react'
import { FiArrowRight } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import BookingDetailsStep from '../components/booking/BookingDetailsStep'
import BookingSteps from '../components/booking/BookingSteps'
import BookingTabs from '../components/booking/BookingTabs'
import DateTimeStep from '../components/booking/DateTimeStep'
import MeetingTypeCard from '../components/booking/MeetingTypeCard'
import '../styles/BookMeeting.css'
import AnimatedOrbitBackground from '../components/AnimatedOrbitBackground/AnimatedOrbitBackground'

function BookMeeting() {
  const navigate = useNavigate()

  const [selectedType, setSelectedType] = useState('introduction')
  const [currentStep, setCurrentStep] = useState(1)
  const [selectedDate, setSelectedDate] = useState(undefined)
  const [selectedTime, setSelectedTime] = useState(null)

  const advisor = {
    firstName: 'Nayiri',
    lastName: 'Saba',
  }
  return (
    <div className="book-meeting-page">
           {/* Background decoration */}
            <AnimatedOrbitBackground />
      <div className="booking-header">
        <div className="booking-logo-container">
          <img src={orbitLogo} alt="Orbit" className="booking-logo" />
        </div>

        <h1>Welcome to Orbit</h1>

        <p>
          Manage your workspace, clients, and automate
          <br />
          workflows.
        </p>
      </div>

      <div
        className={`booking-card ${
          currentStep === 2
            ? 'booking-card-date-time'
            : currentStep === 3
              ? 'booking-card-details'
              : ''
        }`}
      >
        <BookingTabs />

        <BookingSteps currentStep={currentStep} />

        {currentStep === 1 && (
          <div className="booking-content">
            <div className="booking-section-header">
              <h2>What would you like to book?</h2>
              <span>CONSULTATION TYPE</span>
            </div>

            <div className="meeting-type-grid">
              <MeetingTypeCard
                title="Introduction Meeting"
                tag="Presentation 1 · Corporate Introduction"
                description="Learn about the advisor, their services, partner companies and approach."
                selected={selectedType === 'introduction'}
                onClick={() => setSelectedType('introduction')}
              />

              <MeetingTypeCard
                title="Continue My Financial Sessions"
                tag="Follow-up Consultation"
                description="Already met with the advisor? Schedule your next education or planning session."
                selected={selectedType === 'follow-up'}
                onClick={() => setSelectedType('follow-up')}
              />
            </div>

            <div className="booking-actions">
              <button type="button" className="continue-button" onClick={() => setCurrentStep(2)}>
                Continue to Date & Time
                <FiArrowRight />
              </button>
            </div>

            <div className="booking-login">
              Already have an advisor account?{' '}
              <button
                type="button"
                className="advisor-login-link"
                onClick={() => navigate('/login')}
              >
                Advisor Login
              </button>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <DateTimeStep
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            selectedTime={selectedTime}
            setSelectedTime={setSelectedTime}
            onBack={() => setCurrentStep(1)}
            onContinue={() => setCurrentStep(3)}
          />
        )}
        {currentStep === 3 && (
          <BookingDetailsStep
            selectedType={selectedType}
            selectedDate={selectedDate}
            selectedTime={selectedTime}
            advisor={advisor}
            onBack={() => setCurrentStep(2)}
            onChangeBooking={() => setCurrentStep(2)}
          />
        )}
      </div>
    </div>
  )
}

export default BookMeeting
