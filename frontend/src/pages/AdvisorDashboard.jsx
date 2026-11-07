import { useEffect, useState } from 'react'
import '../styles/AdvisorDashboard.css'
import DashboardSchedule from '../components/dashboard/DashboardSchedule'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import DashboardTasks from '../components/dashboard/DashboardTasks'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'
import { withAuthCredentials } from '../services/AuthApi'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

function AdvisorDashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  const advisorId = 1 // Hardcoded for this example, or pull from auth state

  const [tasks, setTasks] = useState([])
  const [schedule, setSchedule] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    const fetchAllDashboardData = async () => {
      try {
        if (active) setLoading(true)

        // Fetch tasks, schedule, and clients concurrently
        const [tasksRes, scheduleRes, clientsRes, summaryData] = await Promise.all([
          fetch(`${API_BASE_URL}/advisors/${advisorId}/tasks`, withAuthCredentials()),
          fetch(`${API_BASE_URL}/advisors/${advisorId}/schedule`, withAuthCredentials()),
          fetch(`${API_BASE_URL}/advisors/${advisorId}/clients`, withAuthCredentials()),
          getAdvisorDashboard(),
        ])

        if (!tasksRes.ok || !scheduleRes.ok || !clientsRes.ok) {
          throw new Error('Failed to fetch dashboard data')
        }

        const [tasksData, scheduleData, clientsData] = await Promise.all([
          tasksRes.json(),
          scheduleRes.json(),
          clientsRes.json(),
        ])

        if (active) {
          setTasks(tasksData)
          setSchedule(scheduleData)
          setClients(clientsData)
          setDashboardData(summaryData)
        }
      } catch (err) {
        if (active) setError(err.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    void fetchAllDashboardData()

    return () => {
      active = false
    }
  }, [advisorId])

  const handleTaskUpdated = (updatedTask) => {
    setTasks((currentTasks) =>
      currentTasks.map((task) => (task.id === updatedTask.id ? { ...task, ...updatedTask } : task)),
    )
  }

  if (loading) {
    return <p>Please wait</p>
  }

  if (error || !dashboardData) {
    return <p role="alert">Could not load dashboard data: {error}</p>
  }

  return (
    <main className="advisor-dashboard">
      <DashboardSummary
        dashboardSummaryData={dashboardData.dashboardSummaryData}
        tasks={tasks}
        schedule={schedule}
        clients={clients}
      />

      <div className="dashboard-overview">
        <div className="dashboard-card">
          <DashboardSchedule scheduleData={schedule} />
        </div>
        <div className="dashboard-card">
          <DashboardTasks priorityTasks={tasks} onTaskUpdated={handleTaskUpdated} />
        </div>
      </div>
    </main>
  )
}

export default AdvisorDashboard
