import { Outlet } from 'react-router-dom'
import { mockAdvisor } from '../../data/mockDashboardData'
import Navbar from './Navbar'

function AdvisorLayout() {
  return (
    <div className="advisor-layout">
      <Navbar user={mockAdvisor} />
      <Outlet />
    </div>
  )
}

export default AdvisorLayout
