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

const formatShortDate = (timestamp) => {
  if (!timestamp) return ''
  const safeString = typeof timestamp === 'string' ? timestamp.replace(' ', 'T') : timestamp
  const date = new Date(safeString)
  if (Number.isNaN(date.getTime())) return ''

  return date.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
  })
}

const getCompletionStatus = (item) => item.completionStatus?.trim().toLowerCase()

const isMeetingOverdue = (item, now = new Date()) => {
  const status = getCompletionStatus(item)
  if (!item.time || status === 'completed' || status === 'cancelled') return false

  const timestamp = typeof item.time === 'string' ? item.time.replace(' ', 'T') : item.time
  const meetingTime = new Date(timestamp)

  return !Number.isNaN(meetingTime.getTime()) && meetingTime < now
}

const getMeetingStatusLabel = (item, overdue) => {
  const status = getCompletionStatus(item)
  if (status === 'completed') return 'Completed'
  if (status === 'cancelled') return 'Cancelled'
  return overdue ? 'Overdue' : 'Scheduled'
}

const getActionLabel = (item) => {
  const status = getCompletionStatus(item)
  if (status === 'completed' || status === 'cancelled') return 'View Details'

  return /zoom|google meet|microsoft teams|\bteams\b|video|virtual/i.test(
    item.locationOrPlatform || '',
  )
    ? 'Join Call'
    : 'View Details'
}

function DashboardSchedule({ scheduleData }) {
  return (
    <div className="dashboard-schedule">
      <h2>Today's Schedule & Consultations</h2>
      {scheduleData.map((item, index) => {
        const overdue = isMeetingOverdue(item)
        const statusLabel = getMeetingStatusLabel(item, overdue)

        return (
          <div
            key={item.id || `${item.time}-${item.clientName}`}
            className={`schedule-item${overdue ? ' overdue' : ''}`}
          >
            <span className="meeting-time">
              <div className={`item-time ${index === 0 ? 'text-blue' : 'item-time'}`}>
                {formatShortTime(item.time)}
              </div>
              <div className="item-duration">{item.duration}</div>
              <div className="item-date">{formatShortDate(item.time)}</div>
            </span>
            <span className="meeting-details">
              <div className="item-client-name-category">
                <span className="item-client-name">{item.clientName}</span>
                <span className="item-category">{item.category}</span>
              </div>
              <div className="item-agenda"> Agenda: {item.agenda}</div>
              <div className={`item-status${overdue ? ' overdue-status' : ''}`}>{statusLabel}</div>
              {item.locationOrPlatform && (
                <div className="item-location">{item.locationOrPlatform}</div>
              )}
            </span>
            <span className={`item-time ${index === 0 ? 'full-blue' : 'action-button'}`}>
              {getActionLabel(item)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default DashboardSchedule
