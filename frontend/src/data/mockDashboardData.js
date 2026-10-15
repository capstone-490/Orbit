export const mockAdvisor = {
  firstName: 'Nayiri',
  role: 'ADVISOR',
}

export const mockDashboardSummary = {
  meetingCount: 4,
  criticalActionCount: 1,
}

export const dashboardSummaryData = [
  {
    id: 1,
    title: "TOTAL CLIENTS",
    primaryValue: "10",
    secondaryValue: "+2 this mo",
    icon: "👥", // Or your icon component
  },
  {
    id: 2,
    title: "UPCOMING MEETINGS",
    primaryValue: "4",
    secondaryValue: "Next: 10:00 AM",
    icon: "📅",
  },
  {
    id: 3,
    title: "PENDING TASKS",
    primaryValue: "5",
    secondaryValue: "2 overdue",
    icon: "📋",
    alert: true,
  },
  {
    id: 4,
    title: "PENDING FNA / PLANS",
    primaryValue: "4",
    secondaryValue: "2 FNAs - 1 financial plan",
    icon: "✨",
  },
];