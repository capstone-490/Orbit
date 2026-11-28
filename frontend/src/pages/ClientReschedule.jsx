import { DayPicker } from '@daypicker/react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getClientReschedule, rescheduleClientMeeting } from '../services/MeetingApi'
import '@daypicker/react/style.css'
import '../styles/ClientReschedule.css'

function ClientReschedule() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [meeting, setMeeting] = useState(null)
  const [selectedDate, setSelectedDate] = useState()
  const [selectedTime, setSelectedTime] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    let active = true
    getClientReschedule(token)
      .then((details) => {
        if (active) setMeeting(details)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [token])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (!selectedDate || !selectedTime) {
      setError('Choose a new date and time.')
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
      setError('Choose a future date and time.')
      return
    }

    setSaving(true)
    try {
      const updated = await rescheduleClientMeeting(token, newStart.toISOString())
      setMeeting((current) => ({ ...current, meeting_date: updated.meeting_date }))
      setSuccess(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="client-reschedule-page">
      <section className="client-reschedule-card">
        <h1>Reschedule your meeting</h1>
        {loading && <p>Loading your meeting...</p>}
        {!loading && error && !meeting && <p role="alert">{error}</p>}
        {meeting && (
          <>
            <p>
              Meeting with {meeting.advisor_name}: {new Date(meeting.meeting_date).toLocaleString()}{' '}
              ({meeting.duration_minutes} min)
            </p>
            {success ? (
              <p role="status">
                Your meeting has been rescheduled. Google Calendar will send you an updated
                invitation.
              </p>
            ) : (
              <form onSubmit={handleSubmit}>
                <DayPicker
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  disabled={{ before: new Date() }}
                  startMonth={new Date()}
                />
                <label htmlFor="client-reschedule-time">New start time</label>
                <input
                  id="client-reschedule-time"
                  type="time"
                  value={selectedTime}
                  onChange={(event) => setSelectedTime(event.target.value)}
                  required
                />
                {error && <p role="alert">{error}</p>}
                <button type="submit" disabled={saving || !selectedDate || !selectedTime}>
                  {saving ? 'Rescheduling...' : 'Confirm new time'}
                </button>
              </form>
            )}
          </>
        )}
      </section>
    </main>
  )
}

export default ClientReschedule
