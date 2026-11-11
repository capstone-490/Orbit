// Substantial AI assistance used; verified with frontend tests.
import '../../styles/DashboardPriorityActions.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const formatShortDate = (dueDate) => {
  const date = new Date(`${dueDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
}

// Badge text and colour for each urgent follow-up.
export const getDueBadge = (action) => {
  if (action.urgency === 'overdue') return { label: 'OVERDUE', tone: 'danger' }
  if (action.days_until_due === 0) return { label: 'TODAY', tone: 'danger' }
  if (action.days_until_due === 1) return { label: 'TOMORROW', tone: 'warning' }
  return { label: formatShortDate(action.due_date), tone: 'neutral' }
}

// Urgent follow-ups, shown inside the dashboard's Priority Tasks card.
function DashboardPriorityActions({ actions, total, loading, error, onRetry, onComplete }) {
  const [completingIds, setCompletingIds] = useState(() => new Set())
  const [completeError, setCompleteError] = useState('')

  const handleComplete = async (followUpId) => {
    setCompletingIds((current) => new Set(current).add(followUpId))
    setCompleteError('')
    try {
      await onComplete(followUpId)
    } catch (err) {
      console.error('Failed to complete follow-up:', err)
      setCompleteError('Could not update follow-up. Please try again.')
    } finally {
      setCompletingIds((current) => {
        const next = new Set(current)
        next.delete(followUpId)
        return next
      })
    }
  }

  const renderBody = () => {
    if (loading) {
      return (
        <p className="urgent-followups-message" role="status">
          Loading urgent follow-ups…
        </p>
      )
    }

    if (error) {
      return (
        <div className="urgent-followups-error" role="alert">
          <span>{error}</span>
          <button type="button" className="urgent-followups-retry" onClick={onRetry}>
            Try again
          </button>
        </div>
      )
    }

    if (actions.length === 0) {
      return (
        <p className="urgent-followups-message">
          No urgent follow-ups. You&apos;re all caught up.
        </p>
      )
    }

    return (
      <ul className="urgent-followups-list">
        {actions.map((action) => {
          const badge = getDueBadge(action)

          return (
            <li
              key={action.follow_up_id}
              className={`urgent-followup-item urgency-${action.urgency}`}
            >
              <input
                type="checkbox"
                className="urgent-followup-checkbox"
                aria-label={`Mark "${action.reason}" as completed`}
                checked={false}
                disabled={completingIds.has(action.follow_up_id)}
                onChange={() => handleComplete(action.follow_up_id)}
              />
              <div className="urgent-followup-details">
                <span className="urgent-followup-title">{action.reason}</span>
                <span className="urgent-followup-meta">
                  {action.client_name} · {action.urgency_reason}
                  {action.priority === 'High' && action.urgency !== 'high_priority'
                    ? ' · High priority'
                    : ''}
                </span>
              </div>
              <span className={`urgent-followup-badge tone-${badge.tone}`}>{badge.label}</span>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <section className="urgent-followups" aria-labelledby="urgent-followups-title">
      <div className="urgent-followups-header">
        <h3 id="urgent-followups-title" className="urgent-followups-title">
          Urgent Follow-Ups
        </h3>
        {!loading && !error && total > 0 && (
          <Link className="urgent-followups-link" to="/follow-ups">
            View all ({total})
          </Link>
        )}
      </div>
      {completeError && (
        <p className="urgent-followups-error" role="alert">
          {completeError}
        </p>
      )}
      {renderBody()}
    </section>
  )
}

export default DashboardPriorityActions