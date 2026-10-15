import '../../styles/DashboardSummary.css'

function DashboardSummary({ dashboardSummaryData }) {
  return (
    <section className="dashboard-summary">
      {dashboardSummaryData.map((item) => (
        <span key={item.id} className="summary-card">
          <span className="card-header">
            <span className="card-title">{item.title}</span>
            <span className="card-icon">{item.icon}</span>
          </span>
          <span className="card-body">
            <span className="primary-value">{item.primaryValue}</span>
            <span className={`secondary-value ${item.alert ? "alert" : ""}`}>
              {item.secondaryValue}
            </span>
          </span>
        </span>
      ))}
    </section>
  )
}

export default DashboardSummary