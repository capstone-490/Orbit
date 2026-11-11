export const TASK_STATUSES = [
  { value: 'TO_DO', label: 'To do' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'IN_REVIEW', label: 'In review' },
  { value: 'COMPLETED', label: 'Completed' },
]

export const isTaskCompleted = (task) => task.status === 'COMPLETED'
