import '../../styles/DashboardHeader.css'

function DashboardHeader({ advisorName, meetingCount, criticalActionCount }) {
  return (
    <section className="dashboard-header">
      <h1>Good morning, {advisorName}.</h1>

      <p>
        You have {meetingCount} meetings and{' '}
        <span className="critical-action">{criticalActionCount} critical fiduciary action</span>{' '}
        scheduled for today.
      </p>
    </section>
  )
}

export default DashboardHeader
