import '../../styles/DashboardSummary.css'

const isTaskOverdue = (task, now) => {
  if (!task.dueDate) return false

  const dueDate = new Date(`${task.dueDate}T00:00:00`)
  if (Number.isNaN(dueDate.getTime())) return false

  return dueDate < new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

const formatMeetingTime = (timestamp) => {
  if (!timestamp) return 'No upcoming meetings'

  const safeString = typeof timestamp === 'string' ? timestamp.replace(' ', 'T') : timestamp
  const date = new Date(safeString)

  return Number.isNaN(date.getTime()) ? 'Invalid Date' : date.toLocaleString()
}

function DashboardSummary({ dashboardSummaryData, tasks, schedule, clients }) {
  const clientCount = clients?.length ?? dashboardSummaryData.totalClient
  const meetingCount = schedule?.length ?? dashboardSummaryData.nbMeetings
  const nextMeeting = schedule
    ? schedule.length > 0
      ? formatMeetingTime(schedule[0].time)
      : 'No upcoming meetings'
    : dashboardSummaryData.nextMeeting
  const pendingTaskCount =
    tasks?.filter((task) => !task.completed).length ?? dashboardSummaryData.pendingTasks
  const overdueTaskCount = tasks
    ? tasks.filter((task) => !task.completed && isTaskOverdue(task, new Date())).length
    : dashboardSummaryData.overdueTasks

  const now = new Date()
  const clientNewCount =
    clients?.filter((client) => {
      const rawTimestamp = client.createdAt ?? client.created_at
      if (!rawTimestamp) return false

      const isoString =
        typeof rawTimestamp === 'string' ? rawTimestamp.replace(' ', 'T') : rawTimestamp
      const clientDate = new Date(isoString)

      return (
        !Number.isNaN(clientDate.getTime()) &&
        clientDate.getFullYear() === now.getFullYear() &&
        clientDate.getMonth() === now.getMonth()
      )
    }).length ?? 0

  return (
    <section className="dashboard-summary">
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">TOTAL CLIENTS</span>
          <span className="card-icon">👥</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{clientCount}</span>
          <span className={`secondary-value ${clientNewCount > 0 ? 'alert' : ''}`}>
            +{clientNewCount} this month
          </span>
        </span>
      </span>
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">UPCOMING MEETINGS</span>
          <span className="card-icon">📅</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{meetingCount}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.nextMeeting.alert ? 'alert' : ''}`}
          >
            Next: {nextMeeting}
          </span>
        </span>
      </span>
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">PENDING TASKS</span>
          <span className="card-icon">📋</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{pendingTaskCount}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.overdueTasks.alert ? 'alert' : ''}`}
          >
            {overdueTaskCount} overdue
          </span>
        </span>
      </span>
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">PENDING FNA / PLANS</span>{' '}
          {/*to be updated with actual data from the backend*/}
          <span className="card-icon">✨</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{dashboardSummaryData.pendingFNAPlans}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.currentFNAPlans.alert ? 'alert' : ''}`}
          >
            {dashboardSummaryData.currentFNAPlans} FNA / Plans in progress
          </span>
        </span>
      </span>
    </section>
  )
}

export default DashboardSummary
