import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { mockAdvisor } from '../../data/mockDashboardData'
import { getCurrentAdvisor } from '../../services/AuthApi'
import Navbar from './Navbar'

function AdvisorLayout() {
  const [isAuthenticated, setIsAuthenticated] = useState(null)

  useEffect(() => {
    let active = true
    getCurrentAdvisor()
      .then(() => active && setIsAuthenticated(true))
      .catch(() => active && setIsAuthenticated(false))

    return () => {
      active = false
    }
  }, [])

  if (isAuthenticated === null) return <p role="status">Checking session...</p>
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div className="advisor-layout">
      <Navbar user={mockAdvisor} />
      <Outlet />
    </div>
  )
}

export default AdvisorLayout
