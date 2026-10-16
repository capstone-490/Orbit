export const mockAdvisor = {
  firstName: 'Nayiri',
  role: 'ADVISOR',
}

export const mockDashboardSummary = {
  meetingCount: 4,
  criticalActionCount: 1,
}

export const dashboardSummaryData = {
  totalClient: 10,
  addedClient: 2,
  nbMeetings: 4,
  nextMeeting: "10:00 AM",
  pendingTasks: 5,
  overdueTasks:2,
  pendingFNAPlans: 4,
  currentFNAPlans: 2,
};

export const mockScheduleData = [
  {
    id: 1,
    time: "10:00 AM",
    duration: "45 min", 
    clientName: "Sarah Smith",
    category: "Financial Planning",
    agenda: "Q4 Liquidity Strategy & irrevocable trust distribution timing",
    statusText: "AI Dossier Ready",
    statusType: "success", 
    locationOrPlatform: null,
    actionButton: {
      label: "Join Google Meet",
      type: "primary", 
      icon: "video"
    }
  },
  {
    id: 2,
    time: "02:00 PM",
    duration: "60 min",
    clientName: "David Sterling",
    category: "Tax Strategy",
    agenda: "Tax-loss harvesting across taxable sleeves; CPA Robert Cole joining",
    statusText: null,
    statusType: null,
    locationOrPlatform: "Zoom Pro",
    actionButton: {
      label: "Open",
      type: "outline", 
      icon: "external-link"
    }
  },
  {
    id: 3,
    time: "03:30 PM",
    duration: "30 min",
    clientName: "Jonathan Wright",
    category: "Audit Review",
    agenda: "Institutional cash flow yield verification & liquidity reserve sync",
    statusText: "Pre-read delivered",
    statusType: "success",
    locationOrPlatform: null,
    actionButton: {
      label: "Dossier",
      type: "outline",
      icon: "folder"
    }
  },
  {
    id: 4,
    time: "04:15 PM",
    duration: "30 min",
    clientName: "Dr. Aris Thorne",
    category: "Annual Review",
    agenda: "529 plan updates for grandchildren & revised beneficiary designations",
    statusText: null,
    statusType: null,
    locationOrPlatform: "Conference Room B",
    actionButton: {
      label: "Agenda",
      type: "outline",
      icon: "file-text"
    }
  }
];

export const mockPriorityTasks = [
  {
    id: 1,
    taskTitle: "Follow up after Corporate Introduction",
    clientName: "Sarah Smith",
    dueDate: "2026-10-16", 
    tag: "TODAY",
    completed: false
  },
  {
    id: 2,
    taskTitle: "Schedule Insurance Education (FC3)",
    clientName: "Elena Rostova",
    dueDate: "2026-10-17",
    tag: "TOMORROW",
    completed: false
  },
  {
    id: 3,
    taskTitle: "Prepare personalized financial plan",
    clientName: "Marcus Sterling",
    dueDate: "2026-10-20",
    tag: "TUE, OCT 20",
    completed: false
  },
  {
    id: 4,
    taskTitle: "Review Q4 Portfolio Allocation",
    clientName: "David Vance",
    dueDate: "2026-10-23",
    tag: "FRI, OCT 23",
    completed: false
  },
  {
    id: 5,
    taskTitle: "Finalize estate and trust documentation",
    clientName: "Rachel Chen",
    dueDate: "2026-10-27",
    tag: "TUE, OCT 27",
    completed: false
  }
];