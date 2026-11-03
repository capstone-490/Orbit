import { FiCheck } from 'react-icons/fi'

function MeetingTypeCard({ title, tag, description, selected, onClick }) {
  return (
    <button
      type="button"
      className={`meeting-type-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="meeting-card-header">
        <h3>{title}</h3>

        {selected && (
          <span className="selected-check">
            <FiCheck />
          </span>
        )}
      </div>

      <span className="meeting-tag">{tag}</span>

      <p>{description}</p>
    </button>
  )
}

export default MeetingTypeCard
