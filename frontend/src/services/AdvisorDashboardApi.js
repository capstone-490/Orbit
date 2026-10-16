import {
  mockAdvisor,
  mockDashboardSummary,
} from '../data/mockDashboardData'

export async function getAdvisorDashboard() {
  return {
    advisor: mockAdvisor,
    dashboardSummary: mockDashboardSummary,
  }
}