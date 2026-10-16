import DashboardHeader from '../components/dashboard/DashboardHeader'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import DashboardTasks from '../components/dashboard/DashboardTasks'
import DashboardSchedule from '../components/dashboard/DashboardSchedule'
import { mockAdvisor, mockDashboardSummary, dashboardSummaryData, mockScheduleData, mockPriorityTasks } from '../data/mockDashboardData'

function AdvisorDashboard() {
  return (
    <main className="advisor-dashboard">
      <DashboardHeader
        advisorName={mockAdvisor.firstName}
        meetingCount={mockDashboardSummary.meetingCount}
        criticalActionCount={mockDashboardSummary.criticalActionCount}
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