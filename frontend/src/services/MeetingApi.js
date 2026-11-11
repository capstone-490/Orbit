const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

async function readError(response) {
  try {
    const data = await response.json()

    if (typeof data.detail === 'string') {
      return data.detail
    }
  } catch {
    // Fall back to the standard error message.
  }

  return 'Unable to reschedule the meeting. Please try again.'
}

function requirePositiveId(value, fieldName) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${fieldName} must be a positive integer.`)
  }
}

export async function getAdvisorMeetings(advisorId) {
  requirePositiveId(advisorId, 'advisorId')

  const response = await fetch(`${API_BASE_URL}/meetings/${advisorId}`, {
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error('Unable to load meetings.')
  }

  return response.json()
}

export async function rescheduleMeeting(meetingId, newStart) {
  requirePositiveId(meetingId, 'meetingId')

  if (typeof newStart !== 'string' || !newStart.trim() || Number.isNaN(Date.parse(newStart))) {
    throw new Error('newStart must be a valid date.')
  }

  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/reschedule`, {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      new_start: newStart,
    }),
  })

  if (!response.ok) {
    const message = await readError(response)
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  return response.json()
}
