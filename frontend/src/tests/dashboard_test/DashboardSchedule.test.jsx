import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'
import '@testing-library/jest-dom/vitest'
import DashboardSchedule from '../../components/dashboard/DashboardSchedule'

afterEach(() => cleanup())

describe('DashboardSchedule Component', () => {
  const mockScheduleData = [
    {
      id: 1,
      time: '2026-10-25T09:00:00',
      duration: '45 mins',
      clientName: 'Alice Johnson',
      category: 'Financial Review',
      agenda: 'Quarterly asset assessment',
      statusText: 'Confirmed',
      actionButtonLabel: 'Join Call',
    },
    {
      id: 2,
      time: '2026-10-25T11:30:00',
      duration: '30 mins',
      clientName: 'Bob Smith',
      category: 'Initial Consultation',
      locationOrPlatform: 'Zoom Meeting',
      agenda: 'New portfolio setup',
      actionButtonLabel: 'View Details',
    },
  ]

  test('renders the schedule title and meeting items correctly', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    // Check heading
    expect(screen.getByText("Today's Schedule & Consultations")).toBeInTheDocument()

    // Check client names and categories
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Financial Review')).toBeInTheDocument()
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
    expect(screen.getByText('Initial Consultation')).toBeInTheDocument()
  })

  test('renders meeting times, durations, and agendas', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getByText('9:00AM')).toBeInTheDocument()
    expect(screen.getByText('45 mins')).toBeInTheDocument()
    expect(screen.getByText(/Quarterly asset assessment/i)).toBeInTheDocument()

    expect(screen.getByText('11:30AM')).toBeInTheDocument()
    expect(screen.getByText('30 mins')).toBeInTheDocument()
    expect(screen.getByText(/New portfolio setup/i)).toBeInTheDocument()
  })

  test('renders status text or platform details when available', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getByText('Confirmed')).toBeInTheDocument()
    expect(screen.getByText('Zoom Meeting')).toBeInTheDocument()
  })

  test('renders action button labels correctly', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    expect(screen.getByText('Join Call')).toBeInTheDocument()
    expect(screen.getByText('View Details')).toBeInTheDocument()
  })
})
