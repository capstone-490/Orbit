import { useEffect, useState } from 'react'
import { TASK_STATUSES } from '../data/taskStatuses'
import { API_BASE_URL, getCurrentAdvisor } from '../services/AuthApi'
import '../styles/Tasks.css'

export function TasksList({
  clients = [],
  tasks,
  isLoading,
  error,
  clientsError = '',
  isClientsLoading = false,
  updateError = '',
  createError = '',
  isCreatingTask = false,
  updatingTaskIds = new Set(),
  onStatusChange,
  onCreateTask,
}) {
  const [search, setSearch] = useState('')
  const [selectedClientId, setSelectedClientId] = useState('all')
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDueDate, setNewTaskDueDate] = useState('')
  const [newTaskClientId, setNewTaskClientId] = useState('')
  const [draggedTaskId, setDraggedTaskId] = useState(null)
  const [dropTargetStatus, setDropTargetStatus] = useState(null)
  const searchTerm = search.trim().toLowerCase()
  const filteredTasks = tasks.filter((task) => {
    const matchesSearch = [task.taskTitle, task.clientName].some((value) =>
      value?.toLowerCase().includes(searchTerm),
    )
    const taskClientId = task.clientId ?? task.client_id
    const matchesClient =
      selectedClientId === 'all' || String(taskClientId) === selectedClientId

    return matchesSearch && matchesClient
  })
  const activeTaskCount = filteredTasks.filter((task) => task.status !== 'COMPLETED').length

  const handleCreateTask = async (event) => {
    event.preventDefault()
    const created = await onCreateTask?.({
      taskTitle: newTaskTitle.trim(),
      dueDate: newTaskDueDate,
      clientId: newTaskClientId ? Number(newTaskClientId) : null,
    })

    if (created) {
      setIsAddTaskOpen(false)
      setNewTaskTitle('')
      setNewTaskDueDate('')
      setNewTaskClientId('')
    }
  }

  return (
    <main className="tasks-page">
      <div className="tasks-toolbar">
        <span className="tasks-count">{activeTaskCount} Active Tasks</span>
        <div className="tasks-filter-controls">
          <button
            className="add-task-button"
            type="button"
            aria-label="Add a new task"
            onClick={() => setIsAddTaskOpen(true)}
          >
            + Add Task
          </button>
          <label className="filter-assigned">
            <span className="tasks-visually-hidden">Filter tasks by client</span>
            <select
              className="clients-filter-select"
              value={selectedClientId}
              disabled={isClientsLoading || clients.length === 0}
              onChange={(event) => setSelectedClientId(event.target.value)}
            >
              <option value="all">All Clients</option>
              {clients.map((client) => (
                <option key={client.id} value={String(client.id)}>
                  {client.name}
                </option>
              ))}
            </select>
          </label>
          <label className="tasks-search">
            <span className="tasks-visually-hidden">Search tasks</span>
            <input
              type="search"
              placeholder="Search tasks..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>
      </div>

      {isAddTaskOpen && (
        <div className="task-modal-backdrop">
          <section
            className="task-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-task-title"
          >
            <h2 id="add-task-title">Add Task</h2>
            <form onSubmit={handleCreateTask}>
              <label className="task-form-field">
                <span>Task title</span>
                <input
                  required
                  maxLength={255}
                  value={newTaskTitle}
                  onChange={(event) => setNewTaskTitle(event.target.value)}
                />
              </label>
              <label className="task-form-field">
                <span>Due date</span>
                <input
                  type="date"
                  required
                  value={newTaskDueDate}
                  onChange={(event) => setNewTaskDueDate(event.target.value)}
                />
              </label>
              <label className="task-form-field">
                <span>Client (optional)</span>
                <select
                  value={newTaskClientId}
                  disabled={isClientsLoading || clients.length === 0}
                  onChange={(event) => setNewTaskClientId(event.target.value)}
                >
                  <option value="">No client assigned</option>
                  {clients.map((client) => (
                    <option key={client.id} value={String(client.id)}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </label>
              {createError && (
                <p className="tasks-error" role="alert">
                  {createError}
                </p>
              )}
              <div className="task-modal-actions">
                <button
                  className="task-cancel-button"
                  type="button"
                  disabled={isCreatingTask}
                  onClick={() => setIsAddTaskOpen(false)}
                >
                  Cancel
                </button>
                <button className="add-task-button" type="submit" disabled={isCreatingTask}>
                  {isCreatingTask ? 'Adding...' : 'Add Task'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {isLoading && <p role="status">Loading tasks...</p>}
      {error && (
        <p className="tasks-error" role="alert">
          {error}
        </p>
      )}
      {clientsError && (
        <p className="tasks-error" role="alert">
          {clientsError}
        </p>
      )}
      {updateError && (
        <p className="tasks-error" role="alert">
          {updateError}
        </p>
      )}

      {!isLoading && !error && tasks.length === 0 && (
        <p className="tasks-empty">You don&apos;t have any tasks yet.</p>
      )}

      {!isLoading && !error && tasks.length > 0 && (
        <div className="tasks-board" aria-label="Task board">
          {TASK_STATUSES.map(({ value, label }) => {
            const columnTasks = filteredTasks.filter((task) => task.status === value)

            return (
              <section
                className={`tasks-column tasks-column-${value.toLowerCase()}${dropTargetStatus === value ? ' is-drop-target' : ''}`}
                key={value}
                aria-labelledby={`tasks-column-${value}`}
                onDragOver={(event) => {
                  event.preventDefault()
                  event.dataTransfer.dropEffect = 'move'
                  setDropTargetStatus(value)
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) {
                    setDropTargetStatus(null)
                  }
                }}
                onDrop={(event) => {
                  event.preventDefault()
                  const taskId = String(
                    event.dataTransfer.getData('text/plain') || draggedTaskId || '',
                  )
                  const task = tasks.find((item) => String(item.id) === taskId)

                  if (task && task.status !== value && !updatingTaskIds.has(task.id)) {
                    onStatusChange(task.id, value)
                  }

                  setDraggedTaskId(null)
                  setDropTargetStatus(null)
                }}
              >
                <header className="tasks-column-header">
                  <h2 id={`tasks-column-${value}`}>{label}</h2>
                  <span className="tasks-column-count" aria-label={`${columnTasks.length} tasks`}>
                    {columnTasks.length}
                  </span>
                </header>

                <ul className="tasks-column-list">
                  {columnTasks.map((task) => (
                    <li
                      className={`tasks-card${draggedTaskId === task.id ? ' is-dragging' : ''}`}
                      key={task.id}
                      draggable={!updatingTaskIds.has(task.id)}
                      onDragStart={(event) => {
                        event.dataTransfer.effectAllowed = 'move'
                        event.dataTransfer.setData('text/plain', String(task.id))
                        setDraggedTaskId(task.id)
                      }}
                      onDragEnd={() => {
                        setDraggedTaskId(null)
                        setDropTargetStatus(null)
                      }}
                    >
                      <h3>{task.taskTitle}</h3>
                      <p className="tasks-card-client">{task.clientName || 'No client assigned'}</p>
                      <p className="tasks-card-due-date">
                        Due{' '}
                        {task.dueDate
                          ? new Date(`${task.dueDate}T00:00:00`).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })
                          : 'date not set'}
                      </p>
                      <label className="tasks-status-field">
                        <span className="tasks-visually-hidden">Move {task.taskTitle} to</span>
                        <select
                          className={`tasks-list-status status-${task.status.toLowerCase()}`}
                          value={task.status}
                          disabled={updatingTaskIds.has(task.id)}
                          onChange={(event) => onStatusChange(task.id, event.target.value)}
                        >
                          {TASK_STATUSES.map((status) => (
                            <option key={status.value} value={status.value}>
                            {status.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    </li>
                  ))}
                  {columnTasks.length === 0 && (
                    <li className="tasks-column-empty">
                      {searchTerm || selectedClientId !== 'all' ? 'No matching tasks' : 'No tasks'}
                    </li>
                  )}
                </ul>
              </section>
            )
          })}
        </div>
      )}
    </main>
  )
}

function TasksPage() {
  const [clients, setClients] = useState([])
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isClientsLoading, setIsClientsLoading] = useState(true)
  const [error, setError] = useState('')
  const [clientsError, setClientsError] = useState('')
  const [updateError, setUpdateError] = useState('')
  const [createError, setCreateError] = useState('')
  const [isCreatingTask, setIsCreatingTask] = useState(false)
  const [updatingTaskIds, setUpdatingTaskIds] = useState(() => new Set())

  useEffect(() => {
    let active = true
    const advisorIdPromise = getCurrentAdvisor().then((advisor) => {
      if (!Number.isSafeInteger(advisor.id) || advisor.id <= 0) {
        throw new Error('Unable to identify the signed-in advisor.')
      }

      return advisor.id
    })

    async function loadTasks() {
      try {
        const advisorId = await advisorIdPromise
        const response = await fetch(`${API_BASE_URL}/advisors/${advisorId}/tasks`, {
          credentials: 'include',
        })
        if (!response.ok) {
          throw new Error('Unable to load tasks. Please try again.')
        }

        const data = await response.json()
        if (!Array.isArray(data)) {
          throw new Error('The task list could not be loaded.')
        }

        if (active) setTasks(data)
      } catch (loadError) {
        if (active) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load tasks. Please try again.',
          )
        }
      } finally {
        if (active) setIsLoading(false)
      }
    }

    async function loadClients() {
      try {
        const advisorId = await advisorIdPromise
        const response = await fetch(`${API_BASE_URL}/advisors/${advisorId}/clients`, {
          credentials: 'include',
        })
        if (!response.ok) {
          throw new Error('Unable to load clients. Please try again.')
        }

        const data = await response.json()
        if (!Array.isArray(data)) {
          throw new Error('The client list could not be loaded.')
        }

        if (active) setClients(data)
      } catch (loadError) {
        if (active) {
          setClientsError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load clients. Please try again.',
          )
        }
      } finally {
        if (active) setIsClientsLoading(false)
      }
    }

    void loadTasks()
    void loadClients()

    return () => {
      active = false
    }
  }, [])

  async function handleStatusChange(taskId, status) {
    setUpdatingTaskIds((current) => new Set(current).add(taskId))
    setUpdateError('')

    try {
      const response = await fetch(`${API_BASE_URL}/advisors/tasks/${taskId}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!response.ok) {
        throw new Error('Unable to update task status. Please try again.')
      }

      const updatedTask = await response.json()
      setTasks((current) =>
        current.map((task) => (task.id === taskId ? { ...task, ...updatedTask } : task)),
      )
    } catch (statusError) {
      setUpdateError(
        statusError instanceof Error
          ? statusError.message
          : 'Unable to update task status. Please try again.',
      )
    } finally {
      setUpdatingTaskIds((current) => {
        const next = new Set(current)
        next.delete(taskId)
        return next
      })
    }
  }

  async function handleCreateTask(taskPayload) {
    setIsCreatingTask(true)
    setCreateError('')

    try {
      const advisor = await getCurrentAdvisor()
      if (!Number.isSafeInteger(advisor.id) || advisor.id <= 0) {
        throw new Error('Unable to identify the signed-in advisor.')
      }

      const response = await fetch(`${API_BASE_URL}/advisors/${advisor.id}/tasks`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskPayload),
      })
      if (!response.ok) {
        const responseBody = await response.json().catch(() => null)
        const detail = responseBody?.detail
        throw new Error(
          typeof detail === 'string' ? detail : 'Unable to add task. Please try again.',
        )
      }

      const createdTask = await response.json()
      setTasks((current) => [...current, createdTask])
      return true
    } catch (taskError) {
      setCreateError(
        taskError instanceof Error ? taskError.message : 'Unable to add task. Please try again.',
      )
      return false
    } finally {
      setIsCreatingTask(false)
    }
  }

  return (
    <TasksList
      clients={clients}
      tasks={tasks}
      isLoading={isLoading}
      isClientsLoading={isClientsLoading}
      error={error}
      clientsError={clientsError}
      updateError={updateError}
      createError={createError}
      isCreatingTask={isCreatingTask}
      updatingTaskIds={updatingTaskIds}
      onStatusChange={handleStatusChange}
      onCreateTask={handleCreateTask}
    />
  )
}

export default TasksPage
