// Substantial AI assistance used; verified with frontend tests and production build.
import { useEffect, useRef, useState } from 'react'
import { getMeetingBriefingNotes } from '../../services/MeetingApi'
import '../../styles/BriefingNotesModal.css'

function BriefingNotesModal({ meeting, onClose }) {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const closeButtonRef = useRef(null)

  useEffect(() => {
    let active = true

    const loadNotes = async () => {
      setLoading(true)
      setError('')

      try {
        const data = await getMeetingBriefingNotes(meeting.id)
        if (active) setNotes(data)
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load briefing notes.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadNotes()

    return () => {
      active = false
    }
  }, [meeting.id])


  useEffect(() => {
    const previouslyFocused = document.activeElement

    closeButtonRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab') return

      const dialog = closeButtonRef.current?.closest('[role="dialog"]')
      if (!dialog) return

      const focusable = Array.from(
        dialog.querySelectorAll(
          'button:not(:disabled), [href], input:not(:disabled), ' +
            'select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.getClientRects().length > 0)

      if (focusable.length === 0) {
        event.preventDefault()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)

      if (previouslyFocused instanceof HTMLElement && previouslyFocused.isConnected) {
        previouslyFocused.focus()
      }
    }
  }, [onClose])


  const formatDate = (timestamp) => {
    if (!timestamp) return ''

    const date = new Date(timestamp)
    return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
  }

  return (
    <div className="briefing-overlay">
      <button
        type="button"
        className="briefing-backdrop"
        aria-label="Close briefing notes"
        onClick={onClose}
      />

      <section
        className="briefing-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="briefing-title"
      >
        <header className="briefing-header">
          <div>
            <h2 id="briefing-title">Meeting Details</h2>
          </div>

          <button
            type="button"
            className="briefing-close"
            aria-label="Close"
            onClick={onClose}
            ref={closeButtonRef}
          >
            Ã—
          </button>
        </header>

                <div className="meeting-info">
        <div>
            <span>Client</span>
            <strong>{meeting.clientName}</strong>
        </div>

        <div>
            <span>Date & Time</span>
            <strong>
            {meeting.time
                ? new Date(meeting.time).toLocaleString('en-CA', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                })
                : 'Not available'}
            </strong>
        </div>

        <div>
            <span>Duration</span>
            <strong>{meeting.duration || 'Not available'}</strong>
        </div>

        <div>
            <span>Status</span>
            <strong>{meeting.completionStatus || 'Scheduled'}</strong>
        </div>
        </div>

        <h3 className="briefing-section-title">Briefing Notes</h3>

        <div className="briefing-content">
          {loading && <p role="status">Loading briefing notes...</p>}

          {!loading && error && (
            <p role="alert" className="briefing-error">
              {error}
            </p>
          )}

          {!loading && !error && notes.length === 0 && (
            <p className="briefing-empty">
              No briefing notes are available for this meeting.
            </p>
          )}

          {!loading && !error && notes.length > 0 && (
            <div className="briefing-notes-grid">
              {notes.map((note, index) => (
                <article
                  key={note.id}
                  className={`briefing-note briefing-note-${index % 4}`}
                >
                  <h3>{note.title || 'Untitled Note'}</h3>
                  <p>{note.content}</p>
                  <time dateTime={note.created_at}>
                    {formatDate(note.created_at)}
                  </time>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

export default BriefingNotesModal