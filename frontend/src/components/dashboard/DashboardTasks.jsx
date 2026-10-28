import '../../styles/DashboardTasks.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'

function DashboardTasks({ priorityTasks, onTaskUpdated }) {
  const [updatingTaskIds, setUpdatingTaskIds] = useState(() => new Set())
  const [updateError, setUpdateError] = useState('')

  const getTagStyleClass = (dueDateStr) => {
    const todayStr = '2026-10-16' // Current date (October 16, 2026)
    const tomorrowStr = '2026-10-17' // Tomorrow's date

    if (dueDateStr === todayStr) return 'badge-today'
    if (dueDateStr === tomorrowStr) return 'badge-tomorrow'
    return 'badge-future'
  }

  // 2. Helper function for badge text labels
  const formatDueDate = (dueDateStr) => {
    const todayStr = '2026-10-16'
    const tomorrowStr = '2026-10-17'

    if (dueDateStr === todayStr) return 'TODAY'
    if (dueDateStr === tomorrowStr) return 'TOMORROW'

    const dateObj = new Date(`${dueDateStr}T00:00:00`)
    return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
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
      {priorityTasks.slice(0, 3).map((item) => (
        <div key={item.id} className="task-item">
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
          <span className={`task-due-date ${getTagStyleClass(item.dueDate)}`}>
            {formatDueDate(item.dueDate)}
          </span>
        </div>
      ))}
    </div>
  )
}

export default DashboardTasks
