import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import DashboardTasks from '../../components/dashboard/DashboardTasks'

const renderDashboardTasks = (props) =>
  render(
    <MemoryRouter>
      <DashboardTasks {...props} />
    </MemoryRouter>,
  )

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

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
    renderDashboardTasks({ priorityTasks: mockTasks })

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

  test('shows a message when a task has no assigned client', () => {
    renderDashboardTasks({ priorityTasks: [{ ...mockTasks[0], clientName: null }] })

    expect(screen.getByText('No client assigned')).toBeInTheDocument()
  })

  test('updates task completion through the API and notifies the parent', async () => {
    const updatedTask = { ...mockTasks[0], completed: true }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => updatedTask,
    })
    const onTaskUpdated = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderDashboardTasks({ priorityTasks: mockTasks, onTaskUpdated })
    fireEvent.click(screen.getAllByRole('checkbox')[0])

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8001/advisors/tasks/1',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ completed: true }),
        }),
      )
      expect(onTaskUpdated).toHaveBeenCalledWith(updatedTask)
    })
  })

  test('shows an error and re-enables the checkbox if the update fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(console, 'error').mockImplementation(() => {})

    renderDashboardTasks({ priorityTasks: mockTasks })
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not update task. Please try again.',
    )
    expect(checkbox).toBeEnabled()
  })

  test('links to the Tasks page', () => {
    renderDashboardTasks({ priorityTasks: mockTasks })

    expect(screen.getByRole('link', { name: 'View All (4) Tasks' })).toHaveAttribute(
      'href',
      '/tasks',
    )
  })
})
