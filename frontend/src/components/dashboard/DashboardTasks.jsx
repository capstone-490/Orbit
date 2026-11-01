import '../../styles/DashboardTasks.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'

function DashboardTasks({ priorityTasks, onTaskUpdated }) {
  const [updatingTaskIds, setUpdatingTaskIds] = useState(() => new Set())
  const [updateError, setUpdateError] = useState('')

  const getLocalDateKey = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  }

  const parseDueDate = (dueDate) => {
    if (!dueDate || Number.isNaN(Date.parse(`${dueDate}T00:00:00`))) return null

    return new Date(`${dueDate}T00:00:00`)
  }

  const isTaskOverdue = (item) => {
    if (item.completed) return false

    const dueDate = parseDueDate(item.dueDate)
    return dueDate !== null && getLocalDateKey(dueDate) < getLocalDateKey(new Date())
  }

  const formatDueDate = (dueDateStr) => {
    const date = parseDueDate(dueDateStr)
    if (!date) return ''

    const today = new Date()
    if (getLocalDateKey(date) === getLocalDateKey(today)) return 'TODAY'

    const tomorrow = new Date(today)
    tomorrow.setDate(today.getDate() + 1)
    if (getLocalDateKey(date) === getLocalDateKey(tomorrow)) return 'TOMORROW'

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
  }
  // Handle checking/unchecking the task
  const handleCheckboxChange = async (taskId, completed) => {
    setUpdatingTaskIds((current) => new Set(current).add(taskId))
    setUpdateError('')

    try {
      const response = await fetch(`http://localhost:8001/advisors/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ completed }),
      })

      if (!response.ok) {
        throw new Error('Failed to update task completion status')
      }

      const updatedTask = await response.json()
      onTaskUpdated?.(updatedTask)
    } catch (error) {
      console.error('Error updating task:', error)
      setUpdateError('Could not update task. Please try again.')
    } finally {
      setUpdatingTaskIds((current) => {
        const next = new Set(current)
        next.delete(taskId)
        return next
      })
    }
  }

  return (
    <div className="dashboard-tasks">
      <div className="section-header">
        <span className="priority-task-title">Priority Tasks</span>
        <Link className="all-tasks-link" to="/tasks">
          View All ({priorityTasks.length}) Tasks
        </Link>
      </div>
      <hr className="task-divider" />
      {updateError && <p role="alert">{updateError}</p>}
      {priorityTasks.slice(0, 3).map((item) => {
        const overdue = isTaskOverdue(item)

        return (
          <div key={item.id} className={`task-item${overdue ? ' overdue' : ''}`}>
            <input
              type="checkbox"
              className="task-checkbox"
              checked={Boolean(item.completed)}
              disabled={updatingTaskIds.has(item.id)}
              onChange={(event) => handleCheckboxChange(item.id, event.target.checked)}
            />
            <div className="task-details">
              <span className="task-title">{item.taskTitle}</span>
              <span className="task-client">{item.clientName || 'No client assigned'}</span>
            </div>
            <span className={`task-due-date${overdue ? ' overdue' : ''}`}>
              {overdue ? `OVERDUE · ${formatDueDate(item.dueDate)}` : formatDueDate(item.dueDate)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default DashboardTasks
