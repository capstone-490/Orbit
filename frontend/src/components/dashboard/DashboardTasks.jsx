import '../../styles/DashboardTasks.css'

function DashboardTasks({ priorityTasks }) {
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

  return (
    <div className="dashboard-tasks">
      <h2> Priority Tasks</h2>
      {priorityTasks.slice(0, 3).map((item) => (
        <div key={item.id} className="task-item">
          <input type="checkbox" className="task-checkbox" />
          <div className="task-details">
            <span className="task-title">{item.taskTitle}</span>
            <span className="task-client">{item.clientName}</span>
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
