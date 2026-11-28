
import { useState } from 'react'
import {
  FiClock,
  FiRefreshCw,
  FiTrendingUp,
  FiPlus,
  FiTarget,
  FiCheckCircle,
  FiTrash2,
  FiX,
} from 'react-icons/fi'
import '../../styles/GoalsCard.css'

const HORIZONS = [
  {
    duration: 'Short-term',
    title: 'SHORT-TERM',
    years: '1–3 years',
    icon: FiClock,
    color: 'short',
  },
  {
    duration: 'Medium-term',
    title: 'MID-RANGE',
    years: '3–7 years',
    icon: FiRefreshCw,
    color: 'medium',
  },
  {
    duration: 'Long-term',
    title: 'LONG-TERM',
    years: '7+ years',
    icon:   FiTrendingUp,
    color: 'long',
  },
]

function GoalsCard({
  goals = [],
  loading = false,
  error = '',
  onAddDetails,
  onDelete,
}) {
  const [deletingId, setDeletingId] = useState(null)
  const [goalToDelete, setGoalToDelete] = useState(null)
  const [deleteError, setDeleteError] = useState('')

  const handleDelete = async () => {
    if (!goalToDelete || deletingId !== null) return

    try {
      setDeletingId(goalToDelete.id)
      setDeleteError('')

      await onDelete(goalToDelete.id)

      setGoalToDelete(null)
    } catch (err) {
      setDeleteError(err.message || 'Unable to delete this goal.')
    } finally {
      setDeletingId(null)
    }
  }

  const openDeleteModal = (goal) => {
    setDeleteError('')
    setGoalToDelete(goal)
  }

  const closeDeleteModal = () => {
    if (deletingId !== null) return

    setGoalToDelete(null)
    setDeleteError('')
  }
  return (
    <section className="financial-goals-card">
      <div className="financial-goals-header">
        <div className="financial-goals-title">
          <FiTarget />
          <h3>Financial Goals</h3>
        </div>

        <button
          type="button"
          className="goals-add-button"
          onClick={onAddDetails}
          disabled={loading}
        >
          <FiPlus />
          Add goals
        </button>
      </div>

      {loading ? (
        <p className="goals-loading">Loading financial goals...</p>
      ) : error ? (
        <p className="goals-error" role="alert">{error}</p>
      ) : goals.length === 0 ? (
        <div className="goals-empty-state">
          <FiTarget className="goals-empty-icon" />
          <h4>No financial goals added yet</h4>
          <p>
            Add financial goals to better understand your client's
            priorities and future plans.
          </p>
        </div>
      ) : (
        <div className="goals-horizons">
          {HORIZONS.map((horizon) => {
            const Icon = horizon.icon

            const horizonGoals = goals.filter(
              (goal) => goal.duration === horizon.duration,
            )

            return (
              <section
                className={`goals-horizon-panel ${horizon.color}`}
                key={horizon.duration}
              >
                <div className="goals-horizon-heading">
                  <div className="goals-horizon-label">
                    <Icon />
                    <strong>{horizon.title}</strong>
                    <span>{horizon.years}</span>
                  </div>
                </div>

                {horizonGoals.length === 0 ? (
                  <p className="goals-horizon-empty">
                    No goals added
                  </p>
                ) : (
                  <div className="goals-list">
                    {horizonGoals.map((goal) => (
                      <div className="goals-goal-row" key={goal.id}>
                        <IconCheck className="goals-goal-check" />

                        <span className="goals-goal-name">
                          {goal.name}
                        </span>

                        {goal.category && (
                          <span className="goals-goal-category">
                            {goal.category}
                          </span>
                        )}
                        <button
                          type="button"
                          className="goals-delete-button"
                          onClick={() => openDeleteModal(goal)}
                          disabled={deletingId !== null}
                          aria-label={`Delete ${goal.name}`}
                          title="Delete goal"
                        >
                          <FiTrash2 />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}
      {goalToDelete && (
      <div className="goal-delete-overlay">
        <div
          className="goal-delete-modal"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="goal-delete-title"
          aria-describedby="goal-delete-description"
        >
          <div className="goal-delete-header">
            <div className="goal-delete-icon">
              <FiTrash2 />
            </div>

            <button
              type="button"
              className="goal-delete-close"
              onClick={closeDeleteModal}
              disabled={deletingId !== null}
              aria-label="Close confirmation"
            >
              <FiX />
            </button>
          </div>

          <h3 id="goal-delete-title">Delete financial goal?</h3>

          <p id="goal-delete-description">
            Are you sure you want to delete{' '}
            <strong>{goalToDelete.name}</strong> from this
            client's financial goals?
          </p>

          <p className="goal-delete-warning">
            This action cannot be undone.
          </p>

          {deleteError && (
            <p className="goal-delete-error" role="alert">
              {deleteError}
            </p>
          )}

          <div className="goal-delete-actions">
            <button
              type="button"
              className="goal-delete-cancel"
              onClick={closeDeleteModal}
              disabled={deletingId !== null}
            >
              Cancel
            </button>

            <button
              type="button"
              className="goal-delete-confirm"
              onClick={handleDelete}
              disabled={deletingId !== null}
            >
              {deletingId !== null ? 'Deleting...' : 'Delete goal'}
            </button>
          </div>
        </div>
      </div>
    )}
    </section>
  )
}

function IconCheck({ className }) {
  return <FiCheckCircle className={className} />
}

export default GoalsCard

