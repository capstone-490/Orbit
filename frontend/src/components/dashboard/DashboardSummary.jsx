import '../../styles/DashboardSummary.css'

function DashboardSummary({ dashboardSummaryData }) {
  return (
    <section className="dashboard-summary">
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">TOTAL CLIENTS</span>
          <span className="card-icon">👥</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{dashboardSummaryData.totalClient}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.addedClient.alert ? 'alert' : ''}`}
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
          <span className="primary-value">{dashboardSummaryData.nbMeetings}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.nextMeeting.alert ? 'alert' : ''}`}
          >
            Next: {dashboardSummaryData.nextMeeting}
          </span>
        </span>
      </span>
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">PENDING TASKS</span>
          <span className="card-icon">📋</span>
        </span>
        <span className="card-body">
          <span className="primary-value">{dashboardSummaryData.pendingTasks}</span>
          <span
            className={`secondary-value ${dashboardSummaryData.overdueTasks.alert ? 'alert' : ''}`}
          >
            {dashboardSummaryData.overdueTasks} overdue
          </span>
        </span>
      </span>
      <span className="summary-card">
        <span className="card-header">
          <span className="card-title">PENDING FNA / PLANS</span>
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
