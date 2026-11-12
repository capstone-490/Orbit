// Substantial AI assistance used; verified with frontend tests.
import '../../styles/DashboardPriorityActions.css'
import { useState } from 'react'

// AI next-step suggestions for urgent follow-ups. Purely optional: when AI is
// off or failing this card shows a short note and nothing else is affected.
// The advisor stays in control: a suggestion is only saved when approved.
function DashboardAiCopilot({
  actions,
  actionsLoading,
  aiStatus,
  aiEnabled,
  suggestions,
  onToggleAi,
  onApprove,
  onDismiss,
  onRefresh,
}) {
  const [approvingIds, setApprovingIds] = useState(() => new Set())
  const [actionError, setActionError] = useState('')
  const actionsById = Object.fromEntries(actions.map((action) => [action.follow_up_id, action]))

  const handleApprove = async (suggestion) => {
    setApprovingIds((current) => new Set(current).add(suggestion.follow_up_id))
    setActionError('')
    try {
      await onApprove(suggestion.follow_up_id, suggestion.text)
    } catch (err) {
      console.error('Failed to approve AI suggestion:', err)
      setActionError('Could not save the suggestion. Please try again.')
    } finally {
      setApprovingIds((current) => {
        const next = new Set(current)
        next.delete(suggestion.follow_up_id)
        return next
      })
    }
  }

  const renderBody = () => {
    if (!aiEnabled) {
      return (
        <p className="ai-copilot-message">
          AI suggestions are off. Turn them on to get suggested next steps for urgent follow-ups.
        </p>
      )
    }

    if (actionsLoading || aiStatus === 'loading') {
      return (
        <p className="ai-copilot-message" role="status">
          Generating suggestions…
        </p>
      )
    }

    if (aiStatus === 'disabled') {
      return <p className="ai-copilot-message">AI suggestions are not set up for this workspace.</p>
    }

    if (aiStatus === 'unavailable') {
      return (
        <p className="ai-copilot-message">
          AI suggestions are unavailable right now. Your urgent follow-ups are still up to date.
        </p>
      )
    }

    if (suggestions.length === 0) {
      return <p className="ai-copilot-message">No suggestions right now.</p>
    }

    return (
      <ul className="ai-copilot-list">
        {suggestions.map((suggestion) => {
          const action = actionsById[suggestion.follow_up_id]
          const approving = approvingIds.has(suggestion.follow_up_id)

          return (
            <li key={suggestion.follow_up_id} className="ai-copilot-item">
              <span className="ai-copilot-label">Suggested next step</span>
              {action && <span className="ai-copilot-title">{action.reason}</span>}
              <p className="ai-copilot-text">{suggestion.text}</p>
              {action && <span className="ai-copilot-meta">{action.client_name}</span>}

              {suggestion.approved ? (
                <p className="ai-copilot-approved" role="status">
                  ✓ Saved to follow-up notes
                </p>
              ) : (
                <div className="ai-copilot-actions">
                  <button
                    type="button"
                    className="ai-copilot-button secondary"
                    disabled={approving}
                    onClick={() => onDismiss(suggestion.follow_up_id)}
                  >
                    Dismiss
                  </button>
                  <button
                    type="button"
                    className="ai-copilot-button primary"
                    disabled={approving}
                    onClick={() => handleApprove(suggestion)}
                  >
                    {approving ? 'Saving…' : '✓ Approve'}
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <section className="ai-copilot" aria-labelledby="ai-copilot-title">
      <div className="ai-copilot-header">
        <span className="ai-copilot-icon" aria-hidden="true">
          ✨
        </span>
        <h2 id="ai-copilot-title" className="ai-copilot-heading">
          AI Copilot
        </h2>
        <label className="ai-copilot-toggle">
          <input
            type="checkbox"
            role="switch"
            className="ai-copilot-toggle-input"
            aria-checked={aiEnabled}
            checked={aiEnabled}
            onChange={(event) => onToggleAi(event.target.checked)}
            aria-label="AI suggestions"
          />
          <span className="ai-copilot-toggle-track" aria-hidden="true">
            <span className="ai-copilot-toggle-thumb" />
          </span>
          <span className="ai-copilot-toggle-text">{aiEnabled ? 'On' : 'Off'}</span>
        </label>
        {aiEnabled &&
          !actionsLoading &&
          (aiStatus === 'available' || aiStatus === 'unavailable') && (
            <button
              type="button"
              className="ai-copilot-refresh"
              onClick={onRefresh}
              aria-label="Refresh AI suggestions"
            >
              ↻ Refresh
            </button>
          )}
      </div>
      <hr className="ai-copilot-divider" />
      {actionError && (
        <p className="urgent-followups-error" role="alert">
          {actionError}
        </p>
      )}
      {renderBody()}
    </section>
  )
}

export default DashboardAiCopilot
