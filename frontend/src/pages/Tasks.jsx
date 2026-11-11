import { useEffect, useState } from 'react'
import { TASK_STATUSES } from '../data/taskStatuses'
import '../styles/Tasks.css'

const API_BASE_URL = 'http://localhost:8001'
const ADVISOR_ID = 1

export function TasksList({
  tasks,
  isLoading,
  error,
  updateError = '',
  updatingTaskIds = new Set(),
  onStatusChange,
}) {
  const [search, setSearch] = useState('')
  const [draggedTaskId, setDraggedTaskId] = useState(null)
  const [dropTargetStatus, setDropTargetStatus] = useState(null)
  const searchTerm = search.trim().toLowerCase()
  const filteredTasks = tasks.filter((task) =>
    [task.taskTitle, task.clientName].some((value) =>
      value?.toLowerCase().includes(searchTerm),
    ),
  )
  const activeTaskCount = tasks.filter((task) => task.status !== 'COMPLETED').length

  return (
    <main className="tasks-page">
      <div className="tasks-toolbar">
        <span className="tasks-count">{activeTaskCount} Active Tasks</span>
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

      {isLoading && <p role="status">Loading tasks...</p>}
      {error && <p className="tasks-error" role="alert">{error}</p>}
      {updateError && <p className="tasks-error" role="alert">{updateError}</p>}

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
                      {searchTerm ? 'No matching tasks' : 'No tasks'}
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
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [updateError, setUpdateError] = useState('')
  const [updatingTaskIds, setUpdatingTaskIds] = useState(() => new Set())

  useEffect(() => {
    let active = true

    async function loadTasks() {
      try {
        const response = await fetch(`${API_BASE_URL}/advisors/${ADVISOR_ID}/tasks`)
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

    void loadTasks()

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

  return (
    <TasksList
      tasks={tasks}
      isLoading={isLoading}
      error={error}
      updateError={updateError}
      updatingTaskIds={updatingTaskIds}
      onStatusChange={handleStatusChange}
    />
  )
}

export default TasksPage
