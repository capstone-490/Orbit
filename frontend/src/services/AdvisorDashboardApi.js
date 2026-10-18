import {
  dashboardSummaryData,
  mockAdvisor,
  mockDashboardSummary,
  mockPriorityTasks,
  mockScheduleData,
} from '../data/mockDashboardData'

export async function getAdvisorDashboard() {
  return {
    advisor: mockAdvisor,
    dashboardSummary: mockDashboardSummary,
    dashboardSummaryData: dashboardSummaryData,
    scheduleData: mockScheduleData,
    priorityTasks: mockPriorityTasks,
  }
}
