// Substantial AI assistance used; verified with frontend tests and production build.
import { useState } from 'react'
import { FiBell, FiLogOut, FiMenu, FiUser, FiX } from 'react-icons/fi'
import { NavLink, useNavigate } from 'react-router-dom'
import orbitLogo from '../../assets/orbit-logo.png'
import { logoutAdvisor } from '../../services/AuthApi'
import '../../styles/Navbar.css'

function Navbar({ user }) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  async function handleSignOut() {
    try {
      await logoutAdvisor()
    } finally {
      setMenuOpen(false)
      navigate('/login', { replace: true })
    }
  }

  function closeMenu() {
    setMenuOpen(false)
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <img src={orbitLogo} alt="Orbit" className="orbit-logo" />

        <span className="orbit-name">Orbit</span>
        <span className="advisor-label">{user.role}</span>
      </div>

      <button
        type="button"
        className="navbar-menu-toggle"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={menuOpen}
        aria-controls="navbar-navigation"
      >
        {menuOpen ? <FiX size={24} /> : <FiMenu size={24} />}
      </button>

      <div
        id="navbar-navigation"
        className={`navbar-content ${menuOpen ? 'navbar-content-open' : ''}`}
      >
        <div className="navbar-links">
          <NavLink to="/dashboard" onClick={closeMenu}>Dashboard</NavLink>
          <NavLink to="/clients" onClick={closeMenu}>Clients</NavLink>
          <NavLink to="/calendar" onClick={closeMenu}>Calendar</NavLink>
          <NavLink to="/follow-ups" onClick={closeMenu}>Follow-Ups</NavLink>
          <NavLink to="/tasks" onClick={closeMenu}>Tasks</NavLink>
          <NavLink to="/documents" onClick={closeMenu}>Documents</NavLink>
          <NavLink to="/ai-review" onClick={closeMenu}>AI Review</NavLink>
          <NavLink to="/activity" onClick={closeMenu}>Activity</NavLink>
        </div>

        <div className="navbar-profile">
          <FiBell className="notification-icon" size={20} />

          <span className="profile-avatar">
            <FiUser size={18} />
          </span>

          <button
            type="button"
            className="logout-button"
            aria-label="Logout"
            onClick={handleSignOut}
          >
            <FiLogOut aria-hidden="true" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
