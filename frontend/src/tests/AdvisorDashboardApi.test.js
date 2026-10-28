import { describe, expect, test } from 'vitest'
import {
  dashboardSummaryData,
  mockAdvisor,
  mockDashboardSummary,
  mockPriorityTasks,
  mockScheduleData,
} from '../data/mockDashboardData'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'

describe('getAdvisorDashboard', () => {
  test('returns the advisor dashboard data used by the dashboard page', async () => {
    await expect(getAdvisorDashboard()).resolves.toEqual({
      advisor: mockAdvisor,
      dashboardSummary: mockDashboardSummary,
      dashboardSummaryData,
      scheduleData: mockScheduleData,
      priorityTasks: mockPriorityTasks,
    })
  })
})
