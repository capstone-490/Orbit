import '../../styles/DashboardSchedule.css'

const formatShortTime = (timestamp) => {
  if (!timestamp) return ''
  const safeString = typeof timestamp === 'string' ? timestamp.replace(' ', 'T') : timestamp
  const date = new Date(safeString)
  if (Number.isNaN(date.getTime())) return ''

  // Format to 12-hour time and remove spaces (e.g., "10:00 PM" -> "10:00PM")
  return date
    .toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
    .replace(/\s+/g, '')
}

function DashboardSchedule({ scheduleData }) {
  return (
    <div className="dashboard-schedule">
      <h2>Today's Schedule & Consultations</h2>
      {scheduleData.map((item, index) => (
        <div key={item.id || `${item.time}-${item.clientName}`} className="schedule-item">
          <span className="meeting-time">
            <div className={`item-time ${index === 0 ? 'text-blue' : 'item-time'}`}>
              {formatShortTime(item.time)}
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
            {item.actionButtonLabel}
          </span>
        </div>
      ))}
    </div>
  )
}

export default DashboardSchedule
