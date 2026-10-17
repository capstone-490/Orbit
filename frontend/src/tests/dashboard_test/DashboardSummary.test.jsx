import { describe, test, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import DashboardSummary from '../../components/dashboard/DashboardSummary';

afterEach(() => {
  cleanup();
});

describe('DashboardSummary Component', () => {
  const mockSummaryData = {
    totalClient: 142,
    addedClient: 12,
    nbMeetings: 5,
    nextMeeting: 'Tomorrow at 10 AM',
    pendingTasks: 8,
    overdueTasks: 2,
    pendingFNAPlans: 4,
    currentFNAPlans: 3
  };

  test('renders all card titles and icons correctly', () => {
    render(<DashboardSummary dashboardSummaryData={mockSummaryData} />);

    expect(screen.getByText('TOTAL CLIENTS')).toBeInTheDocument();
    expect(screen.getByText('UPCOMING MEETINGS')).toBeInTheDocument();
    expect(screen.getByText('PENDING TASKS')).toBeInTheDocument();
    expect(screen.getByText('PENDING FNA / PLANS')).toBeInTheDocument();
  });

  test('renders primary metric values for all cards', () => {
    render(<DashboardSummary dashboardSummaryData={mockSummaryData} />);

    expect(screen.getByText('142')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });
});