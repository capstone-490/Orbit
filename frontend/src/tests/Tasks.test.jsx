import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TasksPage, { TasksList } from '../pages/Tasks'

vi.mock('../services/AuthApi', () => ({
  API_BASE_URL: 'http://localhost:8001',
  getCurrentAdvisor: vi.fn().mockResolvedValue({ id: 5 }),
}))

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
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

  it('lists assigned clients and filters tasks by the selected client', () => {
    render(
      <TasksList
        clients={[
          { id: 1, name: 'Sarah Smith' },
          { id: 2, name: 'Alex Jones' },
        ]}
        tasks={[
          {
            id: 1,
            clientId: 1,
            taskTitle: 'Call Sarah',
            clientName: 'Sarah Smith',
            status: 'TO_DO',
          },
          {
            id: 2,
            clientId: 2,
            taskTitle: 'Review Alex',
            clientName: 'Alex Jones',
            status: 'TO_DO',
          },
        ]}
        isLoading={false}
        error=""
      />,
    )

    const clientFilter = screen.getByRole('combobox', { name: 'Filter tasks by client' })
    expect(clientFilter.querySelectorAll('option')).toHaveLength(3)

    fireEvent.change(clientFilter, { target: { value: '2' } })

    expect(screen.getByText('Review Alex')).toBeInTheDocument()
    expect(screen.queryByText('Call Sarah')).not.toBeInTheDocument()
    expect(screen.getByText('1 Active Tasks')).toBeInTheDocument()
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
        tasks={[{ id: 1, taskTitle: 'Call client', clientName: 'Sarah Smith', status: 'TO_DO' }]}
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
  it('creates a task and shows it on the board', async () => {
    const fetchMock = vi.fn((url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 2,
            taskTitle: 'Call Sarah',
            dueDate: '2026-11-20',
            clientId: 7,
            clientName: 'Sarah Smith',
            status: 'TO_DO',
          }),
        })
      }

      return Promise.resolve({
        ok: true,
        json: async () =>
          url.endsWith('/clients')
            ? [{ id: 7, name: 'Sarah Smith' }]
            : [{ id: 1, taskTitle: 'Review portfolio', status: 'TO_DO' }],
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<TasksPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add a new task' }))

    fireEvent.change(screen.getByLabelText('Task title'), {
      target: { value: 'Call Sarah' },
    })
    fireEvent.change(screen.getByLabelText('Due date'), {
      target: { value: '2026-11-20' },
    })
    fireEvent.change(screen.getByLabelText('Client (optional)'), {
      target: { value: '7' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Task', exact: true }))

    expect(await screen.findByText('Call Sarah')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8001/advisors/5/tasks',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({
          taskTitle: 'Call Sarah',
          dueDate: '2026-11-20',
          clientId: 7,
        }),
      }),
    )
  })

  it('keeps the task form open and shows an API error', async () => {
    const fetchMock = vi.fn((url, options) =>
      Promise.resolve(
        options?.method === 'POST'
          ? {
              ok: false,
              json: async () => ({ detail: 'Unable to save task.' }),
            }
          : {
              ok: true,
              json: async () => (url.endsWith('/clients') ? [] : []),
            },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<TasksPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add a new task' }))
    fireEvent.change(screen.getByLabelText('Task title'), {
      target: { value: 'Call Sarah' },
    })
    fireEvent.change(screen.getByLabelText('Due date'), {
      target: { value: '2026-11-20' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Task', exact: true }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to save task.')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('loads the full advisor task list and passes it to TasksList', async () => {
    const tasks = [
      {
        id: 1,
        clientId: 7,
        taskTitle: 'Review portfolio',
        clientName: 'Sarah Smith',
        status: 'TO_DO',
      },
    ]
    const clients = [{ id: 7, name: 'Sarah Smith' }]
    const fetchMock = vi.fn((url) =>
      Promise.resolve({
        ok: true,
        json: async () => (url.endsWith('/tasks') ? tasks : clients),
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<TasksPage />)

    expect(await screen.findByText('Review portfolio')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/5/tasks', {
      credentials: 'include',
    })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/advisors/5/clients', {
      credentials: 'include',
    })
    expect(screen.getByRole('option', { name: 'Sarah Smith' })).toBeInTheDocument()
  })

  it('reports a task-loading error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url) =>
        Promise.resolve(
          url.endsWith('/tasks') ? { ok: false } : { ok: true, json: async () => [] },
        ),
      ),
    )

    render(<TasksPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load tasks. Please try again.',
    )
  })

  it('persists a changed task status', async () => {
    const tasks = [{ id: 1, taskTitle: 'Review portfolio', status: 'TO_DO' }]
    const fetchMock = vi.fn((url, options) => {
      if (options?.method === 'PATCH') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: 1, status: 'IN_REVIEW' }),
        })
      }

      return Promise.resolve({
        ok: true,
        json: async () => (url.endsWith('/tasks') ? tasks : []),
      })
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
        credentials: 'include',
        body: JSON.stringify({ status: 'IN_REVIEW' }),
      }),
    )
  })
})
