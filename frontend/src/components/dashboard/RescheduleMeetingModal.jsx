import { DayPicker } from '@daypicker/react'
import { useState } from 'react'
import '@daypicker/react/style.css'
import { rescheduleMeeting } from '../../services/MeetingApi'
import '../../styles/RescheduleMeetingModal.css'

function RescheduleMeetingModal({ meeting, onClose, onSuccess }) {
  const [selectedDate, setSelectedDate] = useState(undefined)
  const [selectedTime, setSelectedTime] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!meeting) return null

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (!selectedDate || !selectedTime) {
      setError('Please select a date and time.')
      return
    }

    const [hours, minutes] = selectedTime.split(':').map(Number)
    const newStart = new Date(
      selectedDate.getFullYear(),
      selectedDate.getMonth(),
      selectedDate.getDate(),
      hours,
      minutes,
    )

    if (newStart <= new Date()) {
      setError('Please select a future date and time.')
      return
    }

    setSaving(true)

    try {
      await rescheduleMeeting(meeting.id, newStart.toISOString())
      await onSuccess()
      onClose()
    } catch (err) {
      if (err.status === 409) {
        setError(err.message || 'This time slot is unavailable.')
      } else {
        setError(err.message || 'Unable to reschedule the meeting.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="reschedule-overlay">
      <button
        type="button"
        className="reschedule-backdrop"
        aria-label="Close reschedule dialog"
        onClick={onClose}
        disabled={saving}
      />

      <section
        className="reschedule-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reschedule-title"
      >
        <div className="reschedule-header">
          <h2 id="reschedule-title">Reschedule Meeting</h2>
          <button type="button" onClick={onClose} disabled={saving} aria-label="Close">
            ×
          </button>
        </div>

        <p>
          Choose a new date and time for your meeting
          {meeting.clientName ? ` with ${meeting.clientName}` : ''}.
        </p>

        <form onSubmit={handleSubmit}>
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={setSelectedDate}
            disabled={{ before: new Date() }}
            startMonth={new Date()}
          />

          <label htmlFor="reschedule-time">New start time</label>
          <input
            id="reschedule-time"
            type="time"
            value={selectedTime}
            onChange={(event) => setSelectedTime(event.target.value)}
            required
          />

          {error && (
            <p role="alert" className="reschedule-error">
              {error}
            </p>
          )}

          <div className="reschedule-actions">
            <button type="button" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" disabled={saving || !selectedDate || !selectedTime}>
              {saving ? 'Rescheduling...' : 'Confirm Reschedule'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default RescheduleMeetingModal
