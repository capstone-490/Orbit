import { FiBell, FiUser } from 'react-icons/fi'
import { NavLink } from 'react-router-dom'
import orbitLogo from '../../assets/orbit-logo.png'
import '../../styles/Navbar.css'

function Navbar({ user }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <img src={orbitLogo} alt="Orbit" className="orbit-logo" />

        <span className="orbit-name">Orbit</span>
        <span className="advisor-label">{user.role}</span>
      </div>

      <div className="navbar-links">
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/clients">Clients</NavLink>
        <NavLink to="/calendar">Calendar</NavLink>
        <NavLink to="/follow-ups">Follow-Ups</NavLink>
        <NavLink to="/tasks">Tasks</NavLink>
        <NavLink to="/documents">Documents</NavLink>
        <NavLink to="/ai-review">AI Review</NavLink>
        <NavLink to="/activity">Activity</NavLink>
      </div>

      <div className="navbar-profile">
        <FiBell className="notification-icon" size={20} />

        <span className="profile-avatar">
          <FiUser size={18} />
        </span>
      </div>
    </nav>
  )
}

export default Navbar
