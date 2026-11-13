import { FiCheck } from 'react-icons/fi'

const DEFAULT_TITLES = ['Select Type', 'Date & Time', 'Details']

function BookingSteps({ currentStep, titles = DEFAULT_TITLES }) {
  const steps = titles.map((title, index) => ({ number: index + 1, title }))

  return (
    <div className="booking-steps">
      {steps.map((step, index) => (
        <div className="step-wrapper" key={step.number}>
          <div
            className={`booking-step ${currentStep === step.number ? 'active' : currentStep > step.number ? 'completed' : ''}`}
          >
            <div className="step-number">
              {currentStep > step.number ? <FiCheck /> : step.number}
            </div>

            <div className="step-text">
              <span className="step-label">STEP {step.number}</span>

              <p>{step.title}</p>
            </div>
          </div>

          {index < steps.length - 1 && (
            <div className={`step-line ${currentStep > step.number ? 'completed' : ''}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default BookingSteps
