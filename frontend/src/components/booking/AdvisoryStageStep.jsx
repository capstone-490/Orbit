// Substantial AI assistance used; verified with frontend tests and production build.

import { FiArrowLeft, FiArrowRight, FiCheck } from 'react-icons/fi'

function AdvisoryStageStep({ stages, selectedStageId, onSelectStage, onBack, onContinue }) {
  return (
    <div className="booking-content advisory-stage-content">
      <div className="advisory-stage-heading">
        <h2>Continue Your Financial Journey</h2>
        <p>Select the next step in your personalized financial advisory experience.</p>
      </div>

      <fieldset className="advisory-stage-list">
        <legend className="visually-hidden">Advisory stage</legend>

        {stages.map((stage) => {
          const Icon = stage.icon
          const selected = stage.id === selectedStageId

          return (
            <label key={stage.id} className={`advisory-stage-option ${selected ? 'selected' : ''}`}>
              <input
                type="radio"
                name="advisory-stage"
                value={stage.id}
                checked={selected}
                onChange={() => onSelectStage(stage.id)}
                className="visually-hidden"
              />

              <span className="stage-icon" aria-hidden="true">
                <Icon />
              </span>

              <span className="stage-info">
                <span className="stage-badge">Stage {stage.stage}</span>
                <span className="stage-title">{stage.title}</span>
                <span className="stage-duration">· {stage.duration} min</span>
              </span>

              <span className="stage-radio" aria-hidden="true">
                {selected && <FiCheck />}
              </span>
            </label>
          )
        })}
      </fieldset>

      <div className="date-time-actions">
        <button type="button" className="back-button" onClick={onBack}>
          <FiArrowLeft />
          Back to Session Type
        </button>

        <button
          type="button"
          className="continue-button"
          disabled={!selectedStageId}
          onClick={onContinue}
        >
          Continue to Date & Time
          <FiArrowRight />
        </button>
      </div>
    </div>
  )
}

export default AdvisoryStageStep
