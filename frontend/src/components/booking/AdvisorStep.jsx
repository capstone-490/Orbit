import { useEffect, useState } from 'react'
import { FiArrowRight, FiCheck, FiUser } from 'react-icons/fi'
import { getBookableAdvisors } from '../../services/BookingApi'

function AdvisorStep({ selectedAdvisorId, onSelectAdvisor, onContinue, onAdvisorLogin }) {
  const [advisors, setAdvisors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Bumped by "Try Again" to load the advisors again
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    // Ignore a response that arrives after the step is closed or retried
    let ignore = false

    getBookableAdvisors()
      .then((result) => {
        if (!ignore) {
          setAdvisors(result)
        }
      })
      .catch((loadError) => {
        if (!ignore) {
          setError(loadError.message)
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [attempt])

  const loadAdvisors = () => {
    setLoading(true)
    setError(null)
    setAttempt((previous) => previous + 1)
  }

  return (
    <div className="booking-content">
      <div className="booking-section-header">
        <h2>Who would you like to meet with?</h2>
        <span>CHOOSE YOUR ADVISOR</span>
      </div>

      {loading && <p className="advisor-step-message">Loading advisors...</p>}

      {!loading && error && (
        <div className="advisor-step-message" role="alert">
          <p>{error}</p>
          <button type="button" className="back-button" onClick={loadAdvisors}>
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && advisors.length === 0 && (
        <p className="advisor-step-message">
          No advisors are accepting online bookings right now. Please check back later.
        </p>
      )}

      {!loading && !error && advisors.length > 0 && (
        <fieldset className="advisory-stage-list">
          <legend className="visually-hidden">Choose an advisor</legend>

          {advisors.map((advisor) => {
            const selected = advisor.id === selectedAdvisorId

            return (
              <label
                key={advisor.id}
                className={`advisory-stage-option ${selected ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="advisor"
                  value={advisor.id}
                  checked={selected}
                  onChange={() => onSelectAdvisor(advisor)}
                  className="visually-hidden"
                />

                <span className="stage-icon" aria-hidden="true">
                  <FiUser />
                </span>

                <span className="stage-info">
                  <span className="stage-title">{advisor.username}</span>
                </span>

                <span className="stage-radio" aria-hidden="true">
                  {selected && <FiCheck />}
                </span>
              </label>
            )
          })}
        </fieldset>
      )}

      <div className="booking-actions">
        <button
          type="button"
          className="continue-button"
          disabled={!selectedAdvisorId}
          onClick={onContinue}
        >
          Continue to Session Type
          <FiArrowRight />
        </button>
      </div>

      <div className="booking-login">
        Already have an advisor account?{' '}
        <button type="button" className="advisor-login-link" onClick={onAdvisorLogin}>
          Advisor Login
        </button>
      </div>
    </div>
  )
}

export default AdvisorStep
