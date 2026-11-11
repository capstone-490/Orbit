// Substantial AI assistance used; verified with frontend tests.
const formatShortDate = (dueDate) => {
  const date = new Date(`${dueDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
}

// Badge text and colour for each urgent follow-up.
export const getDueBadge = (action) => {
  if (action.urgency === 'overdue') return { label: 'OVERDUE', tone: 'danger' }
  if (action.days_until_due === 0) return { label: 'TODAY', tone: 'danger' }
  if (action.days_until_due === 1) return { label: 'TOMORROW', tone: 'warning' }
  return { label: formatShortDate(action.due_date), tone: 'neutral' }
}
