import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TasksPage, { TasksList } from '../pages/Tasks'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('TasksList', () => {
  it('displays the tasks passed through its tasks prop', () => {
    render(
      <TasksList
        tasks={[
          {
            id: 1,
            taskTitle: 'Call client',
            clientName: 'Sarah Smith',
            dueDate: '2026-11-12',
            status: 'TO_DO',
          },
          {
            id: 2,
            taskTitle: 'Prepare review',
            clientName: null,
            dueDate: null,
            status: 'COMPLETED',
          },
        ]}
        isLoading={false}
        error=""
      />,
    )

    expect(screen.getByText('Call client')).toBeInTheDocument()
    expect(screen.getByText('Sarah Smith')).toBeInTheDocument()
    expect(screen.getByText('Prepare review')).toBeInTheDocument()
    expect(screen.getByText('No client assigned')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'To do' })).toContainElement(
      screen.getByText('Call client'),
    )
    expect(screen.getByRole('region', { name: 'Completed' })).toContainElement(
      screen.getByText('Prepare review'),
    )
    expect(screen.getByRole('combobox', { name: 'Move Call client to' })).toHaveValue('TO_DO')
    expect(screen.getByRole('combobox', { name: 'Move Prepare review to' })).toHaveValue(
      'COMPLETED',
    )
  })

  it('filters the passed task list by title and client', () => {
    render(
      <TasksList
        tasks={[
          { id: 1, taskTitle: 'Call client', clientName: 'Sarah Smith', status: 'TO_DO' },
          { id: 2, taskTitle: 'Prepare review', clientName: 'Alex Jones', status: 'TO_DO' },
        ]}
        isLoading={false}
        error=""
      />,
    )

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search tasks' }), {
      target: { value: 'alex' },
    })

    expect(screen.getByText('Prepare review')).toBeInTheDocument()
    expect(screen.queryByText('Call client')).not.toBeInTheDocument()
  })

  it('moves a task to another column when the card is dropped there', () => {
    const onStatusChange = vi.fn()
    const dataTransfer = {
      effectAllowed: '',
      dropEffect: '',
      data: {},
      setData(type, value) {
        this.data[type] = value
      },
      getData(type) {
        return this.data[type] ?? ''
      },
    }

    render(
      <TasksList
        tasks={[
          { id: 1, taskTitle: 'Call client', clientName: 'Sarah Smith', status: 'TO_DO' },
        ]}
        isLoading={false}
        error=""
        onStatusChange={onStatusChange}
      />,
    )

    const card = screen.getByText('Call client').closest('.tasks-card')
    const inProgressColumn = screen.getByRole('region', { name: 'In progress' })

    fireEvent.dragStart(card, { dataTransfer })
    fireEvent.dragOver(inProgressColumn, { dataTransfer })
    fireEvent.drop(inProgressColumn, { dataTransfer })

    expect(onStatusChange).toHaveBeenCalledWith(1, 'IN_PROGRESS')
  })
})

describe('TasksPage', () => {
  it('loads the full advisor task list and passes it to TasksList', async () => {
    const tasks = [
      { id: 1, taskTitle: 'Review portfolio', clientName: 'Sarah Smith', status: 'TO_DO' },
    ]
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => tasks,
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<TasksPage />)

    expect(await screen.findByText('Review portfolio')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/1/tasks')
  })

  it('reports a task-loading error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))

    render(<TasksPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load tasks. Please try again.',
    )
  })

  it('persists a changed task status', async () => {
    const tasks = [{ id: 1, taskTitle: 'Review portfolio', status: 'TO_DO' }]
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => tasks })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, status: 'IN_REVIEW' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<TasksPage />)
    const status = await screen.findByRole('combobox', { name: 'Move Review portfolio to' })
    fireEvent.change(status, { target: { value: 'IN_REVIEW' } })

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Move Review portfolio to' })).toHaveValue(
        'IN_REVIEW',
      )
    })
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://localhost:8001/advisors/tasks/1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'IN_REVIEW' }),
      }),
    )
  })
})
