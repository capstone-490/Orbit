import { useEffect, useState } from 'react'
import DashboardHeader from '../components/dashboard/DashboardHeader'
import DashboardSchedule from '../components/dashboard/DashboardSchedule'
import DashboardSummary from '../components/dashboard/DashboardSummary'
import DashboardTasks from '../components/dashboard/DashboardTasks'
import { getAdvisorDashboard } from '../services/AdvisorDashboardApi'

const API_BASE_URL = 'http://localhost:8001';

function AdvisorDashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  const advisorId = 1; // Hardcoded for this example, or pull from auth state
  
  const [tasks, setTasks] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        if (active) setLoading(true);
        
        // Fetch tasks, schedule, and clients concurrently
        const [tasksRes, scheduleRes, clientsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/advisors/${advisorId}/tasks`),
          fetch(`${API_BASE_URL}/advisors/${advisorId}/schedule`),
          fetch(`${API_BASE_URL}/advisors/${advisorId}/clients`)
        ]);

        if (!tasksRes.ok || !scheduleRes.ok || !clientsRes.ok) {
          throw new Error('Failed to fetch dashboard data');
        }

        const tasksData = await tasksRes.json();
        const scheduleData = await scheduleRes.json();
        const clientsData = await clientsRes.json();

        if (active) {
          setTasks(tasksData);
          setSchedule(scheduleData);
          setClients(clientsData);
        }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    };

    void fetchData();

    return () => {
      active = false;
    };
  }, [advisorId]);

  const handleTaskUpdated = (updatedTask) => {
    setTasks((currentTasks) =>
      currentTasks.map((task) => task.id === updatedTask.id ? { ...task, ...updatedTask } : task)
    )
  }

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
        criticalActionCount={dashboardData.dashboardSummary.criticalActionCount}
      />
      <DashboardSummary dashboardSummaryData={dashboardData.dashboardSummaryData} tasks={tasks} schedule={schedule} clients={clients} />

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
