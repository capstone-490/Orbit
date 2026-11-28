
import { useEffect, useRef, useState } from 'react'
import { createClientNote, getClientNotes } from '../../services/NotesApi'
import '../../styles/ClientNotes.css'

function ClientNotes({ client, clientId }) {
  const [notes, setNotes] = useState([])
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const dialogRef = useRef(null)

  useEffect(() => {
    let active = true

    const fetchNotes = async () => {
      setLoading(true)
      setError('')
      setNotes([])

      try {
        const data = await getClientNotes(clientId)

        if (active) {
          setNotes(data)
        }
      } catch (fetchError) {
        if (active) {
          setError(fetchError.message)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void fetchNotes()

    return () => {
      active = false
    }
  }, [clientId])

  const openDialog = () => {
    setTitle('')
    setContent('')
    setFormError('')
    dialogRef.current?.showModal()
  }

  const closeDialog = () => {
    dialogRef.current?.close()
  }

  const handleAddNote = async (event) => {
    event.preventDefault()

    if (!content.trim() || saving) return

    setSaving(true)
    setFormError('')

    try {
      const newNote = await createClientNote(clientId, {
        title: title.trim() || 'Advisor Note',
        content: content.trim(),
      })

      setNotes((previousNotes) => [
        newNote,
        ...previousNotes,
      ])

      closeDialog()
    } catch (saveError) {
      setFormError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      className="client-notes"
      aria-labelledby="client-notes-heading"
    >
      <div className="client-notes-header">
        <div>
          <h2 id="client-notes-heading">Client Notes</h2>
          <p>Manage advisor notes and meeting preparation.</p>
        </div>

        <button
          type="button"
          className="client-notes-add-button"
          onClick={openDialog}
          disabled={loading || Boolean(error)}
        >
          + Add Note
        </button>
      </div>

      {loading ? (
        <p role="status">Loading client notes...</p>
      ) : error ? (
        <p className="clients-error" role="alert">
          {error}
        </p>
      ) : notes.length === 0 ? (
        <div className="client-notes-empty">
          <h3>No notes yet</h3>
          <p>
            Add a note to keep track of discussions,
            observations and meeting preparation.
          </p>

          <button
            type="button"
            className="client-notes-add-button"
            onClick={openDialog}
          >
            + Add your first note
          </button>
        </div>
      ) : (
        <div className="client-notes-list">
          <p className="client-notes-count">
            {notes.length} {notes.length === 1 ? 'note' : 'notes'}
            {' · Newest first'}
          </p>

          {notes.map((note) => (
            <article className="client-note-card" key={note.id}>
              <div className="client-note-header">
                <h3>{note.title}</h3>

                <time dateTime={note.created_at}>
                  {new Date(note.created_at).toLocaleDateString()}
                </time>
              </div>

              <p className="client-note-content">
                {note.content}
              </p>

              <span className="client-note-author">
                {note.author_type === 'Agent'
                  ? 'AI-generated note'
                  : 'Advisor note'}
              </span>
            </article>
          ))}
        </div>
      )}

      <dialog
        ref={dialogRef}
        className="client-notes-modal"
        aria-labelledby="add-note-heading"
        onCancel={(event) => {
          if (saving) event.preventDefault()
        }}
      >
        <form onSubmit={handleAddNote}>
          <div className="client-notes-modal-header">
            <h2 id="add-note-heading">Add Note</h2>

            <button
              type="button"
              className="client-notes-close"
              aria-label="Close dialog"
              onClick={closeDialog}
              disabled={saving}
            >
              ×
            </button>
          </div>

          <p>Add an advisor note for {client.name}.</p>

          {formError && (
            <p className="clients-error" role="alert">
              {formError}
            </p>
          )}

          <label htmlFor="note-title">Title (optional)</label>

          <input
            id="note-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="e.g. Meeting preparation"
            maxLength={150}
            disabled={saving}
          />

          <label htmlFor="note-content">Note content *</label>

          <textarea
            id="note-content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Write your note here..."
            rows={6}
            maxLength={5000}
            required
            disabled={saving}
          />

          <span className="client-notes-character-count">
            {content.length}/5000
          </span>

          <div className="client-notes-modal-actions">
            <button
              type="button"
              className="client-notes-cancel-button"
              onClick={closeDialog}
              disabled={saving}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="client-notes-add-button"
              disabled={!content.trim() || saving}
            >
              {saving ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </form>
      </dialog>
    </section>
  )
}

export default ClientNotes
