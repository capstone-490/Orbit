import {
  mockAdvisor,
  mockDashboardSummary,
  dashboardSummaryData,
  mockScheduleData,
  mockPriorityTasks,
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
