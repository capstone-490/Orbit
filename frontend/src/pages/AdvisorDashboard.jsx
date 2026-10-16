import { useEffect, useState } from 'react'
import DashboardHeader from '../components/dashboard/DashboardHeader'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'

function AdvisorDashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    const loadDashboard = async () => {
      const data = await getAdvisorDashboard()
      setDashboardData(data)
    }

    loadDashboard()
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
    </main>
  )
}

export default AdvisorDashboard