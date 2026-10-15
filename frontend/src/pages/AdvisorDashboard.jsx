import DashboardHeader from '../components/dashboard/DashboardHeader'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import {mockAdvisor, mockDashboardSummary, dashboardSummaryData} from '../data/mockDashboardData'

function AdvisorDashboard() {
  return (
    <main className="advisor-dashboard">
      <DashboardHeader
        advisorName={mockAdvisor.firstName}
        meetingCount={mockDashboardSummary.meetingCount}
        criticalActionCount={mockDashboardSummary.criticalActionCount}
      />
      <DashboardSummary dashboardSummaryData={dashboardSummaryData} />
    </main>
  )
}

export default AdvisorDashboard