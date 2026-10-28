import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import AdvisorDashboard from '../../pages/AdvisorDashboard'

vi.mock('../../services/AdvisorDashboardApi', () => ({
  getAdvisorDashboard: vi.fn().mockResolvedValue({
    advisor: { firstName: 'Nayiri' },
    dashboardSummary: { meetingCount: 1, criticalActionCount: 0 },
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
})

describe('AdvisorDashboard', () => {
  test('loads advisor tasks, schedule, and clients and displays them', async () => {
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

      if (url.endsWith('/schedule')) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 2,
              time: '2026-10-25T10:00:00',
              duration: '30 mins',
              clientName: 'Sarah Smith',
              category: 'Review',
              agenda: 'Review account',
              statusText: 'Confirmed',
              actionButtonLabel: 'Join',
            },
          ],
        })
      }

      return Promise.resolve({
        ok: true,
        json: async () => [[101, 'Sarah Smith']],
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <AdvisorDashboard />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Call client')).toBeInTheDocument()
    expect(screen.getByText('Join')).toBeInTheDocument()
    expect(screen.getByText('TOTAL CLIENTS')).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3)
      expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/tasks')
      expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/schedule')
      expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/clients')
    })
  })
})
