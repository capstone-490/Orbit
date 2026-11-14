//Above 50% AI generated

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Calendar from '../../pages/Calendar'
import { mapAppointment } from '../../services/Appointment.mapper'
import { calendarApi } from '../../services/CalendarApi'

// Mock calendar API methods to control the data returned by the backend.
vi.mock('../../services/CalendarApi', () => ({
  calendarApi: {
    getAppointments: vi.fn(),
    getGoogleStatus: vi.fn(),
    connectUrl: '/api/google-meet-integration/authorize',
  },
}))

// Mock the authenticated advisor.
vi.mock('../../services/AuthApi', () => ({
  getCurrentAdvisor: vi.fn().mockResolvedValue({ id: 1 }),
}))

// Helper to create dates for a specific time on the current day.
const at = (h, m = 0) => {
  const date = new Date()
  date.setHours(h, m, 0, 0)
  return date
}

// Helper to create a default appointment with optional overrides.
const raw = (over) => ({
  id: 'x',
  kind: 'session',
  typeId: 'investment',
  client: 'John Lee',
  start: at(15).toISOString(),
  end: at(16).toISOString(),
  source: 'orbit',
  ...over,
})

// Helper to simulate the calendar API response.
// Maps appointments and returns only those within the requested date range.
const serve = (list) => (from, to) =>
  Promise.resolve(list.map(mapAppointment).filter((a) => a.start >= from && a.start < to))

// Reset the calendar environment before every test.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })

  // Fix the current date to November 13, 2026, at noon (local time).
  vi.setSystemTime(new Date(2026, 10, 13, 12, 0, 0))
  calendarApi.getGoogleStatus.mockResolvedValue({ connected: true })
  calendarApi.getAppointments.mockImplementation(serve([]))
})

// Restore timers and clear mocks after every test.
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('Calendar', () => {
  it('renders scheduled sessions and busy calendar blocks', async () => {
    calendarApi.getAppointments.mockImplementation(
      serve([
        raw({ id: '1' }),
        {
          id: '2',
          kind: 'busy',
          start: at(12, 30).toISOString(),
          end: at(13, 30).toISOString(),
          source: 'google',
        },
      ]),
    )
    render(<Calendar />)
    expect((await screen.findAllByText(/John Lee/)).length).toBeGreaterThan(0)
    expect(screen.getByText(/Busy/)).toBeInTheDocument()
  })

  it('uses a default style when a session has an unknown type', async () => {
    calendarApi.getAppointments.mockImplementation(
      serve([raw({ typeId: 'does_not_exist', client: 'Unknown Type' })]),
    )
    render(<Calendar />)
    expect((await screen.findAllByText(/Unknown Type/)).length).toBeGreaterThan(0)
  })

  it('counts scheduled sessions but excludes busy blocks from meeting statistics', async () => {
    calendarApi.getAppointments.mockImplementation(
      serve([
        raw({ id: '1' }),
        {
          id: '2',
          kind: 'busy',
          start: at(12, 30).toISOString(),
          end: at(13, 30).toISOString(),
          source: 'google',
        },
      ]),
    )
    render(<Calendar />)
    await userEvent.click(screen.getByRole('tab', { name: 'Day' }))
    expect(await screen.findByText(/1 scheduled appointment · 1h meeting time/)).toBeInTheDocument()
  })

  it('displays a Join Meet link when a session has a meeting URL', async () => {
    calendarApi.getAppointments.mockImplementation(
      serve([raw({ meetUrl: 'https://meet.google.com/abc-defg-hij' })]),
    )
    render(<Calendar />)
    const link = await screen.findByRole('link', { name: /join meet/i })
    expect(link).toHaveAttribute('href', 'https://meet.google.com/abc-defg-hij')
  })

  it("offers to connect when Google isn't connected", async () => {
    calendarApi.getGoogleStatus.mockResolvedValue({ connected: false })
    render(<Calendar />)
    expect(await screen.findByText(/connect google calendar/i)).toBeInTheDocument()
  })

  it('shows an error banner and recovers on Retry', async () => {
    calendarApi.getAppointments
      .mockRejectedValueOnce(new Error('boom'))
      .mockImplementation(serve([]))
    render(<Calendar />)
    expect(await screen.findByText(/couldn't load appointments/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.queryByText(/couldn't load appointments/i)).toBeNull())
  })

  it('shows how many sessions are booked this month', async () => {
    calendarApi.getAppointments.mockImplementation(serve([raw({ id: '1' }), raw({ id: '2' })]))
    render(<Calendar />)
    expect(await screen.findByText(/2 Booked this month/)).toBeInTheDocument()
  })
})
