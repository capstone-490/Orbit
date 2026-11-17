const API_BASE_URL = import.meta.env.VITE_API_URL

// Booking times are shown to clients in Eastern Time
export const BOOKING_TIME_ZONE = 'America/New_York'

const mockAvailableTimes = ['09:30 AM', '10:30 AM', '11:15 AM', '01:30 PM', '02:45 PM', '04:00 PM']

export const getAvailableTimes = async () => {
  return mockAvailableTimes
}

async function readErrorDetail(response) {
  try {
    const data = await response.json()

    if (typeof data.detail === 'string') {
      return data.detail
    }
  } catch {
    // Fall back to the caller's message.
  }

  return null
}

// Advisors who have connected Google and can be booked
export async function getBookableAdvisors() {
  const response = await fetch(`${API_BASE_URL}/google-meet-integration/advisors`)

  if (!response.ok) {
    throw new Error('Unable to load advisors. Please try again.')
  }

  return response.json()
}

const BOOKING_ERROR_MESSAGES = {
  404: 'This advisor is not accepting bookings right now. Please choose another advisor.',
  422: 'Please check your details and the selected time, then try again.',
  502: 'We could not create the Google Meet meeting. Please try again in a moment.',
}

// Creates the Google Calendar event with a Meet link and saves the meeting in Orbit
export async function bookMeeting(advisorId, booking) {
  if (!Number.isSafeInteger(advisorId) || advisorId <= 0) {
    throw new Error('advisorId must be a positive integer.')
  }

  const response = await fetch(`${API_BASE_URL}/google-meet-integration/book/${advisorId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(booking),
  })

  if (!response.ok) {
    // 409 details from the API are already written for the client to read
    const detail = response.status === 409 ? await readErrorDetail(response) : null
    const error = new Error(
      detail ??
        BOOKING_ERROR_MESSAGES[response.status] ??
        'Unable to book the meeting. Please try again.',
    )
    error.status = response.status
    throw error
  }

  return response.json()
}

// Offset of timeZone from UTC, in minutes, at the given instant
function timeZoneOffsetMinutes(instant, timeZone) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(instant)
  const value = (type) => Number(parts.find((part) => part.type === type).value)
  const asUtc = Date.UTC(
    value('year'),
    value('month') - 1,
    value('day'),
    value('hour'),
    value('minute'),
    value('second'),
  )

  return Math.round((asUtc - instant.getTime()) / 60000)
}

function formatOffset(minutes) {
  const sign = minutes < 0 ? '-' : '+'
  const absolute = Math.abs(minutes)
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0')
  const mins = String(absolute % 60).padStart(2, '0')

  return `${sign}${hours}:${mins}`
}

// Turns the picked calendar day and a slot like "01:30 PM" into an ISO
// timestamp with the booking time zone's offset, e.g. 2026-11-19T13:30:00-05:00
export function toBookingStart(date, timeLabel, timeZone = BOOKING_TIME_ZONE) {
  const match = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec(timeLabel?.trim() ?? '')

  if (!(date instanceof Date) || Number.isNaN(date.getTime()) || !match) {
    throw new Error('A valid date and time are required.')
  }

  let hours = Number(match[1]) % 12
  if (match[3].toUpperCase() === 'PM') {
    hours += 12
  }
  const minutes = Number(match[2])

  const year = date.getFullYear()
  const month = date.getMonth()
  const day = date.getDate()

  // Guess the instant as if the wall time were UTC, then correct by the zone's
  // offset; a second pass handles days when daylight saving time changes.
  const wallTimeAsUtc = Date.UTC(year, month, day, hours, minutes)
  let offset = timeZoneOffsetMinutes(new Date(wallTimeAsUtc), timeZone)
  offset = timeZoneOffsetMinutes(new Date(wallTimeAsUtc - offset * 60000), timeZone)

  const pad = (number) => String(number).padStart(2, '0')
  const datePart = `${year}-${pad(month + 1)}-${pad(day)}`
  const timePart = `${pad(hours)}:${pad(minutes)}:00`

  return `${datePart}T${timePart}${formatOffset(offset)}`
}
