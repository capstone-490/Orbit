import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import { mockAdvisor } from '../../data/mockDashboardData'

function AdvisorLayout() {
  return (
    <div className="advisor-layout">
      <Navbar user={mockAdvisor} />
      <Outlet />
    </div>
  )
}

export default AdvisorLayout