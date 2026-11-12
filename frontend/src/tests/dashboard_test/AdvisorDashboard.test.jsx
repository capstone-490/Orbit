import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdvisorDashboard from '../../pages/AdvisorDashboard'
import { getCurrentAdvisor } from '../../services/AuthApi'
import { getAdvisorMeetings, rescheduleMeeting } from '../../services/MeetingApi'

vi.mock('../../services/AuthApi', () => ({
  getCurrentAdvisor: vi.fn(),
}))

vi.mock('../../services/MeetingApi', () => ({
  getAdvisorMeetings: vi.fn(),
  rescheduleMeeting: vi.fn(),
}))

vi.mock('../../hooks/usePriorityActions', () => ({
  usePriorityActions: () => ({
    actions: [],
    total: 0,
    loading: false,
    error: '',
    retry: vi.fn(),
    completeAction: vi.fn(),
    aiStatus: 'disabled',
    suggestions: [],
    approveSuggestion: vi.fn(),
    dismissSuggestion: vi.fn(),
    refreshSuggestions: vi.fn(),
    aiEnabled: true,
    setAiEnabled: vi.fn(),
  }),
}))

vi.mock('../../services/AdvisorDashboardApi', () => ({
  getAdvisorDashboard: vi.fn().mockResolvedValue({
    advisor: { firstName: 'Nayiri' },
    dashboardSummaryData: {
      totalClient: 1,
      addedClient: 0,
      nbMeetings: 1,
      nextMeeting: '10:00 AM',
      pendingTasks: 1,
      overdueTasks: 0,
      pendingFNAPlans: 0,
      currentFNAPlans: 0,
    },
  }),
}))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('AdvisorDashboard', () => {
  test('loads authenticated advisor data and displays real meetings', async () => {
    getCurrentAdvisor.mockResolvedValue({ id: 1 })

    getAdvisorMeetings.mockResolvedValue([
      {
        id: 2,
        client_id: 101,
        advisor_id: 1,
        meeting_date: '2030-10-25T10:00:00',
        duration_minutes: 30,
        completion_status: 'Scheduled',
        client_name: 'Sarah Smith',
      },
    ])

    const fetchMock = vi.fn((url) => {
      if (url.endsWith('/tasks')) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              taskTitle: 'Call client',
              clientName: 'Sarah Smith',
              dueDate: '2026-10-25',
              completed: false,
            },
          ],
        })
      }

      if (url.endsWith('/clients')) {
        return Promise.resolve({
          ok: true,
          json: async () => [[101, 'Sarah Smith']],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <AdvisorDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Call client')).toBeInTheDocument()
    expect(screen.getAllByText('Sarah Smith')).toHaveLength(2)
    expect(screen.getByText('30 min')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reschedule' })).toBeInTheDocument()
    expect(screen.getByText('TOTAL CLIENTS')).toBeInTheDocument()

    await waitFor(() => {
      expect(getCurrentAdvisor).toHaveBeenCalled()
      expect(getAdvisorMeetings).toHaveBeenCalledWith(1)
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/tasks', {
      credentials: 'include',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/clients', {
      credentials: 'include',
    })
  })

  test('shows an error when dashboard API requests fail', async () => {
    getCurrentAdvisor.mockResolvedValue({ id: 1 })
    getAdvisorMeetings.mockResolvedValue([])

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => [],
      }),
    )

    render(
      <MemoryRouter>
        <AdvisorDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load dashboard data: Failed to fetch dashboard data',
    )
  })

  test('refreshes the meeting schedule after a successful reschedule', async () => {
    getCurrentAdvisor.mockResolvedValue({ id: 1 })

    const originalMeeting = {
      id: 2,
      client_id: 101,
      advisor_id: 1,
      meeting_date: '2030-10-25T10:00:00',
      duration_minutes: 30,
      completion_status: 'Scheduled',
      client_name: 'Sarah Smith',
    }

    getAdvisorMeetings.mockResolvedValueOnce([originalMeeting]).mockResolvedValueOnce([
      {
        ...originalMeeting,
        meeting_date: '2030-10-26T14:30:00',
      },
    ])

    rescheduleMeeting.mockResolvedValue({
      id: 2,
      meeting_date: '2030-10-26T14:30:00',
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      }),
    )

    render(
      <MemoryRouter>
        <AdvisorDashboard />
      </MemoryRouter>,
    )

    const rescheduleButton = await screen.findByRole('button', {
      name: 'Reschedule',
    })

    fireEvent.click(rescheduleButton)

    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Select a future date using the calendar.
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 7)

    const dateString = [
      futureDate.getFullYear(),
      String(futureDate.getMonth() + 1).padStart(2, '0'),
      String(futureDate.getDate()).padStart(2, '0'),
    ].join('-')

    const dateCell = document.querySelector(`[data-day="${dateString}"]`)

    expect(dateCell).not.toBeNull()
    fireEvent.click(dateCell.querySelector('button'))

    fireEvent.change(screen.getByLabelText('New start time'), {
      target: { value: '14:30' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Confirm Reschedule' }))

    await waitFor(() => {
      expect(rescheduleMeeting).toHaveBeenCalledOnce()
      expect(getAdvisorMeetings).toHaveBeenCalledTimes(2)
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    expect(getAdvisorMeetings).toHaveBeenLastCalledWith(1)
  })
})
