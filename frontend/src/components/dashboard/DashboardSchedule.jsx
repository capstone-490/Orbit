import '../../styles/DashboardSchedule.css'

function DashboardSchedule({ scheduleData }) {
  return (
    <div className="dashboard-schedule">
      <h2>Today's Schedule & Consultations</h2>
      {scheduleData.map((item, index) => (
        <div key={item.id || `${item.time}-${item.clientName}`} className="schedule-item">
          <span className="meeting-time">
            <div className={`item-time ${index === 0 ? 'text-blue' : 'item-time'}`}>
              {item.time}
            </div>
            <div className="item-duration">{item.duration}</div>
          </span>
          <span className="meeting-details">
            <div className="item-client-name-category">
              <span className="item-client-name">{item.clientName}</span>
              <span className="item-category">{item.category}</span>
            </div>
            <div className="item-agenda"> Agenda: {item.agenda}</div>
            {(item.statusText || item.locationOrPlatform) && (
              <div className="item-status">{item.statusText || item.locationOrPlatform}</div>
            )}
          </span>
          <span className={`item-time ${index === 0 ? 'full-blue' : 'action-button'}`}>
            {item.actionButton.label}
          </span>
        </div>
      ))}
    </div>
  )
}

export default DashboardSchedule