const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const mockAvailableTimes = ['09:30 AM', '10:30 AM', '11:15 AM', '01:30 PM', '02:45 PM', '04:00 PM']

export const getAvailableTimes = async () => {
  return mockAvailableTimes
}

export const createBooking = async (advisorId, bookingData) => {
  const response = await fetch(`${API_URL}/google-meet-integration/book/${advisorId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(bookingData),
  })

  if (!response.ok) {
    throw new Error(`Booking failed: ${response.status}`)
  }

  return response.json()
}
