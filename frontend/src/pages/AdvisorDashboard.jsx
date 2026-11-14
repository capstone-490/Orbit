import { useCallback, useEffect, useState } from 'react'
import '../styles/AdvisorDashboard.css'
import DashboardHeader from '../components/dashboard/DashboardHeader'
import DashboardSchedule from '../components/dashboard/DashboardSchedule'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import DashboardTasks from '../components/dashboard/DashboardTasks'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'
import { getCurrentAdvisor } from '../services/AuthApi'
import { getAdvisorMeetings } from '../services/MeetingApi'

const API_BASE_URL = 'http://localhost:8001'

const mapMeetingsToSchedule = (meetings) =>
  meetings.map((meeting) => ({
    id: meeting.id,
    time: meeting.meeting_date,
    duration: `${meeting.duration_minutes} min`,
    clientName: meeting.client_name,
    category: 'Consultation',
    agenda: '',
    completionStatus: meeting.completion_status,
    locationOrPlatform: null,
  }))

function AdvisorDashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  const [tasks, setTasks] = useState([])
  const [schedule, setSchedule] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    const fetchData = async () => {
      try {
        if (active) {
          setLoading(true)
          setError(null)
        }

        const advisor = await getCurrentAdvisor()
        const advisorId = advisor.id

        const [tasksRes, meetingsData, clientsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/advisors/${advisorId}/tasks`, {
            credentials: 'include',
          }),
          getAdvisorMeetings(advisorId),
          fetch(`${API_BASE_URL}/advisors/${advisorId}/clients`, {
            credentials: 'include',
          }),
        ])

        if (!tasksRes.ok || !clientsRes.ok) {
          throw new Error('Failed to fetch dashboard data')
        }

        const tasksData = await tasksRes.json()
        const clientsData = await clientsRes.json()

        const mappedSchedule = mapMeetingsToSchedule(meetingsData)

        if (active) {
          setTasks(tasksData)
          setSchedule(mappedSchedule)
          setClients(clientsData)
        }
      } catch (err) {
        if (active) setError(err.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    void fetchData()

    return () => {
      active = false
    }
  }, [])

  const handleTaskUpdated = (updatedTask) => {
    setTasks((currentTasks) =>
      currentTasks.map((task) => (task.id === updatedTask.id ? { ...task, ...updatedTask } : task)),
    )
  }
  const handleMeetingRescheduled = useCallback(async () => {
    const advisor = await getCurrentAdvisor()
    const meetingsData = await getAdvisorMeetings(advisor.id)

    setSchedule(mapMeetingsToSchedule(meetingsData))
  }, [])

  useEffect(() => {
    const loadDashboard = async () => {
      const data = await getAdvisorDashboard()
      setDashboardData(data)
    }

    loadDashboard().catch((error) => {
      console.error('Failed to load dashboard:', error)
    })
  }, [])

  if (loading || !dashboardData) {
    return <p>Please wait</p>
  }

  if (error) {
    return <p role="alert">Could not load dashboard data: {error}</p>
  }

  return (
    <main className="advisor-dashboard">
      <DashboardHeader />
      <DashboardSummary
        dashboardSummaryData={dashboardData.dashboardSummaryData}
        tasks={tasks}
        schedule={schedule}
        clients={clients}
      />

      <div className="dashboard-overview">
        <div className="dashboard-card">
          <DashboardSchedule
            scheduleData={schedule}
            onMeetingRescheduled={handleMeetingRescheduled}
          />
        </div>
        <div className="dashboard-card">
          <DashboardTasks priorityTasks={tasks} onTaskUpdated={handleTaskUpdated} />
        </div>
      </div>
    </main>
  )
}

export default AdvisorDashboard
