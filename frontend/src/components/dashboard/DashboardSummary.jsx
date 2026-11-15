import { FiCalendar, FiClipboard, FiClock, FiUsers, FiZap } from 'react-icons/fi'
import '../../styles/DashboardSummary.css'
import { isTaskCompleted } from '../../data/taskStatuses'

const isTaskOverdue = (task, now) => {
  if (!task.dueDate) return false

  const dueDate = new Date(`${task.dueDate}T00:00:00`)
  if (Number.isNaN(dueDate.getTime())) return false

  return dueDate < new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

const parseMeetingTime = (meeting) => {
  if (!meeting.time) return null

  const safeString =
    typeof meeting.time === 'string' ? meeting.time.replace(' ', 'T') : meeting.time

  const meetingTime = new Date(safeString)

  return Number.isNaN(meetingTime.getTime()) ? null : meetingTime
}

const isUpcomingMeeting = (meeting, now) => {
  const status = meeting.completionStatus?.trim().toLowerCase()

  if (status === 'completed' || status === 'cancelled') {
    return false
  }

  const meetingTime = parseMeetingTime(meeting)

  return meetingTime !== null && meetingTime >= now
}

const formatMeetingTime = (timestamp) => {
  if (!timestamp) return 'No upcoming meetings'

  const safeString = typeof timestamp === 'string' ? timestamp.replace(' ', 'T') : timestamp

  const date = new Date(safeString)

  if (Number.isNaN(date.getTime())) {
    return 'No upcoming meetings'
  }

  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function DashboardSummary({ dashboardSummaryData, tasks, schedule, clients }) {
  const now = new Date()

  const clientCount = clients?.length ?? dashboardSummaryData.totalClient
<<<<<<< HEAD
  const upcomingMeetings = schedule
    ?.filter((meeting) => isUpcomingMeeting(meeting, now))
    .sort((first, second) => parseMeetingTime(first) - parseMeetingTime(second))
  const meetingCount = upcomingMeetings?.length ?? dashboardSummaryData.nbMeetings
  const nextMeeting = upcomingMeetings
    ? upcomingMeetings.length > 0
      ? formatMeetingTime(upcomingMeetings[0].time)
      : 'No upcoming meetings'
    : dashboardSummaryData.nextMeeting
  const pendingTaskCount =
    tasks?.filter((task) => !isTaskCompleted(task)).length ?? dashboardSummaryData.pendingTasks
  const overdueTaskCount = tasks
    ? tasks.filter((task) => !isTaskCompleted(task) && isTaskOverdue(task, new Date())).length
    : dashboardSummaryData.overdueTasks
=======
>>>>>>> fd33bdf (Fixed conflicts)

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

  const upcomingMeetings = schedule
    ?.filter((meeting) => isUpcomingMeeting(meeting, now))
    .sort((first, second) => parseMeetingTime(first) - parseMeetingTime(second))

  const meetingCount = upcomingMeetings?.length ?? dashboardSummaryData.nbMeetings

  const nextMeeting = upcomingMeetings
    ? upcomingMeetings.length > 0
      ? formatMeetingTime(upcomingMeetings[0].time)
      : 'No upcoming meetings'
    : typeof dashboardSummaryData.nextMeeting === 'string'
      ? formatMeetingTime(dashboardSummaryData.nextMeeting)
      : 'No upcoming meetings'

  const pendingTaskCount =
    tasks?.filter((task) => !task.completed).length ?? dashboardSummaryData.pendingTasks

  const overdueTaskCount = tasks
    ? tasks.filter((task) => !task.completed && isTaskOverdue(task, now)).length
    : typeof dashboardSummaryData.overdueTasks === 'number'
      ? dashboardSummaryData.overdueTasks
      : 0

  const pendingFNAPlans = dashboardSummaryData.pendingFNAPlans

  const currentFNAPlans =
    typeof dashboardSummaryData.currentFNAPlans === 'number'
      ? dashboardSummaryData.currentFNAPlans
      : 0

  return (
    <section className="dashboard-summary">
<<<<<<< HEAD
      <article className="summary-card" aria-label="Total clients">
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
      </article>
      <article className="summary-card" aria-label="Upcoming meetings">
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
      </article>
      <article className="summary-card" aria-label="Pending tasks">
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
      </article>
      <article className="summary-card" aria-label="Pending FNA / plans">
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
      </article>
=======
      {/* Total Clients */}
      <div className="summary-card">
        <div className="summary-card-content">
          <span className="card-title">TOTAL CLIENTS</span>

          <div className="card-body">
            <span className="primary-value">{clientCount}</span>

            <span className="secondary-value clients-status">+{clientNewCount} this month</span>
          </div>
        </div>

        <div className="card-icon clients-icon">
          <FiUsers />
        </div>
      </div>

      {/* Upcoming Meetings */}
      <div className="summary-card">
        <div className="summary-card-content">
          <span className="card-title">UPCOMING MEETINGS</span>

          <div className="card-body">
            <span className="primary-value">{meetingCount}</span>

            <span className="secondary-value meetings-status">
              <FiClock />
              Next: {nextMeeting}
            </span>
          </div>
        </div>

        <div className="card-icon meetings-icon">
          <FiCalendar />
        </div>
      </div>

      {/* Pending Tasks */}
      <div className="summary-card">
        <div className="summary-card-content">
          <span className="card-title">PENDING TASKS</span>

          <div className="card-body">
            <span className="primary-value">{pendingTaskCount}</span>

            <span className="secondary-value tasks-status">
              {overdueTaskCount > 0 && <FiClock />}
              {overdueTaskCount} overdue
            </span>
          </div>
        </div>

        <div className="card-icon tasks-icon">
          <FiClipboard />
        </div>
      </div>

      {/* Pending FNA / Plans */}
      <div className="summary-card">
        <div className="summary-card-content">
          <span className="card-title">PENDING FNA / PLANS</span>

          <div className="card-body">
            <span className="primary-value">{pendingFNAPlans}</span>

            <span className="secondary-value fna-status">
              {currentFNAPlans} FNA / Plans in progress
            </span>
          </div>
        </div>

        <div className="card-icon fna-icon">
          <FiZap />
        </div>
      </div>
>>>>>>> fd33bdf (Fixed conflicts)
    </section>
  )
}

export default DashboardSummary
