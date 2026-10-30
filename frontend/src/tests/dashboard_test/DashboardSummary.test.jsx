import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import DashboardSummary from '../../components/dashboard/DashboardSummary'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('DashboardSummary Component', () => {
  const mockSummaryData = {
    totalClient: 142,
    addedClient: 12,
    nbMeetings: 5,
    nextMeeting: 'Tomorrow at 10 AM',
    pendingTasks: 8,
    overdueTasks: 2,
    pendingFNAPlans: 4,
    currentFNAPlans: 3,
  }

  test('renders all card titles and icons correctly', () => {
    render(<DashboardSummary dashboardSummaryData={mockSummaryData} />)

    expect(screen.getByText('TOTAL CLIENTS')).toBeInTheDocument()
    expect(screen.getByText('UPCOMING MEETINGS')).toBeInTheDocument()
    expect(screen.getByText('PENDING TASKS')).toBeInTheDocument()
    expect(screen.getByText('PENDING FNA / PLANS')).toBeInTheDocument()
  })

  test('renders primary metric values for all cards', () => {
    render(<DashboardSummary dashboardSummaryData={mockSummaryData} />)

    expect(screen.getByText('142')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  test('excludes completed tasks from the pending task count', () => {
    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        tasks={[{ completed: false }, { completed: true }, { completed: false }]}
      />,
    )

    expect(screen.getByText('2')).toBeInTheDocument()
  })

  test('excludes overdue meetings from the upcoming meeting count', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-30T12:00:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        schedule={[
          { time: '2026-10-30T11:00:00', completionStatus: 'Scheduled' },
          { time: '2026-10-30T16:00:00', completionStatus: 'Scheduled' },
          { time: '2026-10-30T13:00:00', completionStatus: 'Scheduled' },
          { time: '2026-10-30T14:00:00', completionStatus: 'Completed' },
          { time: '2026-10-30T15:00:00', completionStatus: 'Cancelled' },
        ]}
      />,
    )

    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/Next:/)).toHaveTextContent(
      new Date('2026-10-30T13:00:00').toLocaleString(),
    )
  })

  test('counts tasks overdue by date without marking tasks due today overdue', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T13:15:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        tasks={[
          { dueDate: '2026-10-28', completed: false },
          { dueDate: '2026-10-29', completed: false },
          { dueDate: '2026-10-27', completed: true },
          { dueDate: 'invalid', completed: false },
        ]}
      />,
    )

    expect(screen.getByText('1 overdue')).toBeInTheDocument()
  })

  test('excludes completed overdue tasks from the overdue count', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T13:15:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        tasks={[
          { dueDate: '2026-10-28', completed: true },
          { dueDate: '2026-10-27', completed: true },
        ]}
      />,
    )

    expect(screen.getByText('0 overdue')).toBeInTheDocument()
  })

  test('counts clients created during the current month', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T12:00:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        clients={[
          { createdAt: '2026-10-01T10:00:00Z' },
          { createdAt: '2026-10-28T17:57:27.425682+00:00' },
          { createdAt: '2026-09-30T23:59:59Z' },
          { createdAt: 'not-a-date' },
          {},
        ]}
      />,
    )

    expect(screen.getByText('+2 this month')).toBeInTheDocument()
  })

  test('counts all three clients with current-month API timestamps', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T12:00:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        clients={[
          { createdAt: '2026-10-28T17:57:27.425682+00:00' },
          { createdAt: '2026-10-28T17:57:27.425682+00:00' },
          { createdAt: '2026-10-28T17:57:27.425682+00:00' },
        ]}
      />,
    )

    expect(screen.getByText('+3 this month')).toBeInTheDocument()
  })

  test('supports SQL-style client creation timestamps', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T12:00:00'))

    render(
      <DashboardSummary
        dashboardSummaryData={mockSummaryData}
        clients={[{ created_at: '2026-10-28 17:57:27' }]}
      />,
    )

    expect(screen.getByText('+1 this month')).toBeInTheDocument()
  })
})
