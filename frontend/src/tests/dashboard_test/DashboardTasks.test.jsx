import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'
import '@testing-library/jest-dom/vitest'
import DashboardTasks from '../../components/dashboard/DashboardTasks'

afterEach(() => cleanup())

describe('DashboardTasks Component', () => {
  const mockTasks = [
    {
      id: 1,
      taskTitle: 'Follow up after Corporate Introduction',
      clientName: 'Sarah Smith',
      dueDate: '2026-10-16',
      completed: false,
    },
    {
      id: 2,
      taskTitle: 'Schedule Insurance Education (FC3)',
      clientName: 'Elena Rostova',
      dueDate: '2026-10-17',
      completed: false,
    },
    {
      id: 3,
      taskTitle: 'Prepare personalized financial plan',
      clientName: 'Marcus Sterling',
      dueDate: '2026-10-20',
      completed: false,
    },
    {
      id: 4,
      taskTitle: 'Extra Task Beyond Limit',
      clientName: 'David Vance',
      dueDate: '2026-10-30',
      completed: false,
    },
  ]

  test('renders tasks limited by slice constraint and displays titles, clients, and formatted dates', () => {
    render(<DashboardTasks priorityTasks={mockTasks} />)

    // Verify first 3 tasks render
    expect(screen.getByText('Follow up after Corporate Introduction')).toBeInTheDocument()
    expect(screen.getByText('Sarah Smith')).toBeInTheDocument()
    expect(screen.getByText('TODAY')).toBeInTheDocument()

    expect(screen.getByText('Schedule Insurance Education (FC3)')).toBeInTheDocument()
    expect(screen.getByText('TOMORROW')).toBeInTheDocument()

    expect(screen.getByText('Prepare personalized financial plan')).toBeInTheDocument()
    expect(screen.getByText('OCT 20')).toBeInTheDocument()

    // Verify the 4th task is excluded due to slice(0, 3)
    expect(screen.queryByText('Extra Task Beyond Limit')).not.toBeInTheDocument()
  })
})
