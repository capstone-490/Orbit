// Substantial AI assistance used; verified with frontend tests and production build.

import { useState } from 'react'
import { FiArrowRight } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import AdvisoryStageStep from '../components/booking/AdvisoryStageStep'
import BookingDetailsStep from '../components/booking/BookingDetailsStep'
import BookingSteps from '../components/booking/BookingSteps'
import BookingTabs from '../components/booking/BookingTabs'
import DateTimeStep from '../components/booking/DateTimeStep'
import MeetingTypeCard from '../components/booking/MeetingTypeCard'
import { advisoryStages } from '../data/advisoryStages'
import '../styles/BookMeeting.css'
import AnimatedOrbitBackground from '../components/AnimatedOrbitBackground/AnimatedOrbitBackground'

const INTRODUCTION_MEETING = { name: 'Introduction Meeting', duration: 45 }
const FOLLOW_UP_STEP_TITLES = ['Advisory Stage', 'Date & Time', 'Client Details']

function BookMeeting() {
  const navigate = useNavigate()

  const [selectedType, setSelectedType] = useState('introduction')
  const [currentStep, setCurrentStep] = useState(1)
  const [showStagePicker, setShowStagePicker] = useState(false)
  const [selectedStageId, setSelectedStageId] = useState(null)
  const [selectedDate, setSelectedDate] = useState(undefined)
  const [selectedTime, setSelectedTime] = useState(null)

  const advisor = {
    firstName: 'Nayiri',
    lastName: 'Saba',
  }

  const isFollowUp = selectedType === 'follow-up'
  const selectedStage = advisoryStages.find((stage) => stage.id === selectedStageId)

  // What the client is booking, shown on the Date & Time and Details steps
  const meeting =
    isFollowUp && selectedStage
      ? { name: selectedStage.title, duration: selectedStage.duration }
      : INTRODUCTION_MEETING

  // The stepper switches to the follow-up labels once the client is on the stage picker
  const stepTitles =
    isFollowUp && (showStagePicker || currentStep > 1) ? FOLLOW_UP_STEP_TITLES : undefined

  // After the client closes the confirmation pop-up, start a fresh booking
  const resetBooking = () => {
    setSelectedType('introduction')
    setShowStagePicker(false)
    setSelectedStageId(null)
    setSelectedDate(undefined)
    setSelectedTime(null)
    setCurrentStep(1)
  }

  const handleTypeContinue = () => {
    if (isFollowUp) {
      setShowStagePicker(true)
    } else {
      setCurrentStep(2)
    }
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

        <BookingSteps currentStep={currentStep} titles={stepTitles} />

        {currentStep === 1 && !showStagePicker && (
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
              <button type="button" className="continue-button" onClick={handleTypeContinue}>
                {isFollowUp ? 'Choose Your Next Session' : 'Continue to Date & Time'}
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

        {currentStep === 1 && showStagePicker && (
          <AdvisoryStageStep
            stages={advisoryStages}
            selectedStageId={selectedStageId}
            onSelectStage={setSelectedStageId}
            onBack={() => setShowStagePicker(false)}
            onContinue={() => setCurrentStep(2)}
          />
        )}
        {currentStep === 2 && (
          <DateTimeStep
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            selectedTime={selectedTime}
            setSelectedTime={setSelectedTime}
            meetingName={meeting.name}
            duration={meeting.duration}
            backLabel={isFollowUp ? 'Back to Advisory Stage' : 'Back to Session Type'}
            onBack={() => setCurrentStep(1)}
            onContinue={() => setCurrentStep(3)}
          />
        )}
        {currentStep === 3 && (
          <BookingDetailsStep
            selectedType={selectedType}
            meetingName={meeting.name}
            duration={meeting.duration}
            selectedDate={selectedDate}
            selectedTime={selectedTime}
            advisor={advisor}
            onBack={() => setCurrentStep(2)}
            onChangeBooking={() => setCurrentStep(2)}
            onBookingComplete={resetBooking}
          />
        )}
      </div>
    </div>
  )
}

export default BookMeeting
