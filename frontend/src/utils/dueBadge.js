// Substantial AI assistance used; verified with frontend tests.
const formatShortDate = (dueDate) => {
  const date = new Date(`${dueDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
}

// Badge text and colour for each urgent follow-up. Tones match the
// Follow-Up Tracker: overdue (red), today (blue), upcoming (light blue).
export const getDueBadge = (action) => {
  if (action.urgency === 'overdue') return { label: 'OVERDUE', tone: 'overdue' }
  if (action.days_until_due === 0) return { label: 'TODAY', tone: 'today' }
  if (action.days_until_due === 1) return { label: 'TOMORROW', tone: 'upcoming' }
  return { label: formatShortDate(action.due_date), tone: 'upcoming' }
}
