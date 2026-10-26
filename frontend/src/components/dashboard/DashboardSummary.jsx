import '../../styles/DashboardSummary.css'

const formatMeetingTime = (timestamp) => {
  if (!timestamp) return 'No upcoming meetings';

  const safeString = typeof timestamp === 'string' ? timestamp.replace(' ', 'T') : timestamp;
  const date = new Date(safeString);

  return isNaN(date.getTime()) ? 'Invalid Date' : date.toLocaleString();
};

function DashboardSummary({ dashboardSummaryData, tasks, schedule, clients }) {
  const clientCount = clients?.length ?? dashboardSummaryData.totalClient;
  const meetingCount = schedule?.length ?? dashboardSummaryData.nbMeetings;
  const nextMeeting = schedule
    ? schedule.length > 0
      ? formatMeetingTime(schedule[0].time)
      : 'No upcoming meetings'
    : dashboardSummaryData.nextMeeting;
  const pendingTaskCount = tasks?.length ?? dashboardSummaryData.pendingTasks;
  const overdueTaskCount = tasks
    ? tasks.filter((task) => new Date(task.dueDate) < new Date() && !task.completed).length
    : dashboardSummaryData.overdueTasks;

  return (
    <section className="dashboard-summary">
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">TOTAL CLIENTS</span>
          <span className="card-icon">👥</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{clientCount}</span>
          <span
            className={`secondary-value ${clientCount > 0 ? 'alert' : ''}`}
          >
            +{dashboardSummaryData.addedClient} this month
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
          <span className="card-title">PENDING FNA / PLANS</span> {/*to be updated with actual data from the backend*/}
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
