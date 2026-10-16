import { useEffect, useState } from 'react'
import DashboardHeader from '../components/dashboard/DashboardHeader'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import DashboardTasks from '../components/dashboard/DashboardTasks'
import DashboardSchedule from '../components/dashboard/DashboardSchedule'
import { mockAdvisor, mockDashboardSummary, dashboardSummaryData, mockScheduleData, mockPriorityTasks } from '../data/mockDashboardData'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'

function AdvisorDashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    const loadDashboard = async () => {
      const data = await getAdvisorDashboard()
      setDashboardData(data)
    }

    loadDashboard().catch((error) => {
      console.error('Failed to load dashboard:', error)
    })
  }, [])

  if (!dashboardData) {
    return <p>Please wait</p>
  }

  return (
    <main className="advisor-dashboard">
      <DashboardHeader
        advisorName={dashboardData.advisor.firstName}
        meetingCount={dashboardData.dashboardSummary.meetingCount}
        criticalActionCount={
          dashboardData.dashboardSummary.criticalActionCount
        }
      />
      <DashboardSummary dashboardSummaryData={dashboardSummaryData} />

      <div className="dashboard-overview">
        <div className="dashboard-card">
          <DashboardSchedule scheduleData={mockScheduleData} />
        </div>
        <div className="dashboard-card">
          <DashboardTasks priorityTasks={mockPriorityTasks} />
        </div>
      </div>
    </main>
  )
}

export default AdvisorDashboard