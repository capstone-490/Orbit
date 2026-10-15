import DashboardHeader from '../components/dashboard/DashboardHeader'
import {mockAdvisor, mockDashboardSummary} from '../data/mockDashboardData'

function AdvisorDashboard() {
  return (
    <main className="advisor-dashboard">
      <DashboardHeader
        advisorName={mockAdvisor.firstName}
        meetingCount={mockDashboardSummary.meetingCount}
        criticalActionCount={mockDashboardSummary.criticalActionCount}
      />
    </main>
  )
}

export default AdvisorDashboard