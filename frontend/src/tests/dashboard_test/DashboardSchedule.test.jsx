import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import DashboardSchedule from '../../components/dashboard/DashboardSchedule'
import { getMeetingBriefingNotes } from '../../services/MeetingApi'

vi.mock('../../services/MeetingApi', () => ({
  getMeetingBriefingNotes: vi.fn(),
}))

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-29T12:00:00'))
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('DashboardSchedule Component', () => {
  const mockScheduleData = [
    {
      id: 1,
      time: '2026-10-30T09:00:00',
      duration: '45 mins',
      clientName: 'Alice Johnson',
      category: 'Financial Review',
      agenda: 'Quarterly asset assessment',
      completionStatus: 'Scheduled',
      locationOrPlatform: 'Google Meet',
    },
    {
      id: 2,
      time: '2026-10-30T11:30:00',
      duration: '30 mins',
      clientName: 'Bob Smith',
      category: 'Initial Consultation',
      locationOrPlatform: 'Conference Room B',
      agenda: 'New portfolio setup',
      completionStatus: 'Scheduled',
    },
  ]

  test('renders the schedule title and meeting items correctly', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    // Check heading
    expect(
      screen.getByRole('heading', { name: "Today's Schedule & Consultations" }),
    ).toBeInTheDocument()

    // Check client names and categories
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Financial Review')).toBeInTheDocument()
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
    expect(screen.getByText('Initial Consultation')).toBeInTheDocument()
  })

  test('renders meeting times, durations, and agendas', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getAllByText('Oct 30')).toHaveLength(2)
    expect(screen.getByText(/9:00\s*(?:AM|a\.m\.)/i)).toBeInTheDocument()
    expect(screen.getByText(/Quarterly asset assessment/i)).toBeInTheDocument()

    expect(screen.getByText(/11:30\s*(?:AM|a\.m\.)/i)).toBeInTheDocument()
    expect(screen.getByText('30 mins')).toBeInTheDocument()
    expect(screen.getByText(/New portfolio setup/i)).toBeInTheDocument()
  })

  test('derives meeting status from completion state and displays the location', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getAllByText('Scheduled')).toHaveLength(2)
    expect(screen.getByText('Google Meet')).toBeInTheDocument()
    expect(screen.getByText('Conference Room B')).toBeInTheDocument()
  })

  test('renders View Details actions for eligible meetings', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getAllByRole('button', { name: 'View Details' })).toHaveLength(2)

    expect(screen.queryByText('Join Call')).not.toBeInTheDocument()
  })

  test('allows viewing details and briefing notes for cancelled meetings', () => {
    getMeetingBriefingNotes.mockReturnValue(new Promise(() => {}))

    const cancelledMeeting = {
      ...mockScheduleData[0],
      id: 99,
      completionStatus: 'Cancelled',
    }

    render(<DashboardSchedule scheduleData={[cancelledMeeting]} />)

    expect(screen.getByText('Cancelled')).toBeInTheDocument()

    const viewDetailsButton = screen.getByRole('button', {
      name: 'View Details',
    })

    fireEvent.click(viewDetailsButton)

    const dialog = screen.getByRole('dialog', {
      name: 'Meeting Details',
    })

    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByText('Alice Johnson')).toBeInTheDocument()
    expect(within(dialog).getByText('Cancelled')).toBeInTheDocument()
    expect(getMeetingBriefingNotes).toHaveBeenCalledWith(99)
  })

  test('renders an empty schedule without meeting items', () => {
    render(<DashboardSchedule scheduleData={[]} />)

    expect(
      screen.getByRole('heading', { name: "Today's Schedule & Consultations" }),
    ).toBeInTheDocument()
    expect(document.querySelectorAll('.schedule-item')).toHaveLength(0)
  })

  test('omits a meeting time when the timestamp is invalid', () => {
    render(<DashboardSchedule scheduleData={[{ ...mockScheduleData[0], time: 'not-a-date' }]} />)

    expect(document.querySelector('.meeting-time .item-time')).toBeEmptyDOMElement()
    expect(document.querySelector('.meeting-time .item-date')).toBeEmptyDOMElement()
  })

  test('flags meetings in the past as overdue', () => {
    render(
      <DashboardSchedule
        scheduleData={[
          { ...mockScheduleData[0], id: 3, time: '2026-10-29T11:00:00' },
          { ...mockScheduleData[1], id: 4, time: '2026-10-29T14:00:00' },
        ]}
      />,
    )

    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(document.querySelector('.schedule-item.overdue')).toBeInTheDocument()
    expect(document.querySelectorAll('.schedule-item.overdue')).toHaveLength(1)
  })

  test('does not flag completed meetings in the past as overdue', () => {
    render(
      <DashboardSchedule
        scheduleData={[
          {
            ...mockScheduleData[0],
            time: '2026-10-29T11:00:00',
            completionStatus: 'Completed',
          },
        ]}
      />,
    )

    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(document.querySelector('.schedule-item.overdue')).not.toBeInTheDocument()
  })

  test('does not flag cancelled meetings in the past as overdue', () => {
    render(
      <DashboardSchedule
        scheduleData={[
          {
            ...mockScheduleData[0],
            time: '2026-10-29T11:00:00',
            completionStatus: 'Cancelled',
          },
        ]}
      />,
    )

    expect(screen.getByText('Cancelled')).toBeInTheDocument()
    expect(document.querySelector('.schedule-item.overdue')).not.toBeInTheDocument()
  })

  test('opens meeting details with briefing notes for the selected meeting', () => {
    getMeetingBriefingNotes.mockReturnValue(new Promise(() => {}))

    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    const briefingButtons = screen.getAllByRole('button', {
      name: 'View Details',
    })

    expect(briefingButtons).toHaveLength(2)

    fireEvent.click(briefingButtons[0])

    const dialog = screen.getByRole('dialog', {
      name: 'Meeting Details',
    })

    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByText('Alice Johnson')).toBeInTheDocument()
    expect(getMeetingBriefingNotes).toHaveBeenCalledWith(1)
  })
})
