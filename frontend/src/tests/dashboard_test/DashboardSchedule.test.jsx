import {afterEach, describe, expect, test } from 'vitest';
import {cleanup, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import DashboardSchedule from '../../components/dashboard/DashboardSchedule';

afterEach(() => cleanup())

describe('DashboardSchedule Component', () => {
  const mockScheduleData = [
    {
      time: '09:00 AM',
      duration: '45 mins',
      clientName: 'Alice Johnson',
      category: 'Financial Review',
      agenda: 'Quarterly asset assessment',
      statusText: 'Confirmed',
      actionButton: { label: 'Join Call' },
    },
    {
      time: '11:30 AM',
      duration: '30 mins',
      clientName: 'Bob Smith',
      category: 'Initial Consultation',
      locationOrPlatform: 'Zoom Meeting',
      agenda: 'New portfolio setup',
      actionButton: { label: 'View Details' },
    },
  ];

  test('renders the schedule title and meeting items correctly', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />)

    // Check heading
    expect(screen.getByText("Today's Schedule & Consultations")).toBeInTheDocument()

    // Check client names and categories
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Financial Review')).toBeInTheDocument()
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
    expect(screen.getByText('Initial Consultation')).toBeInTheDocument()
  });

  test('renders meeting times, durations, and agendas', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />);

    expect(screen.getByText('09:00 AM')).toBeInTheDocument();
    expect(screen.getByText('45 mins')).toBeInTheDocument();
    expect(screen.getByText(/Quarterly asset assessment/i)).toBeInTheDocument();

    expect(screen.getByText('11:30 AM')).toBeInTheDocument();
    expect(screen.getByText('30 mins')).toBeInTheDocument();
    expect(screen.getByText(/New portfolio setup/i)).toBeInTheDocument();
  });

  test('renders status text or platform details when available', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />);

    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.getByText('Zoom Meeting')).toBeInTheDocument();
  });

  test('renders action button labels correctly', () => {
    render(<DashboardSchedule scheduleData={mockScheduleData} />);

    expect(screen.getByText('Join Call')).toBeInTheDocument();
    expect(screen.getByText('View Details')).toBeInTheDocument();
  });
});