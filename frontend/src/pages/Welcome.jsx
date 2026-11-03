// AI assistance: Used ChatGPT for implementation guidance and code refinement.

import { FiArrowRight, FiCalendar, FiLogIn, FiUserPlus } from 'react-icons/fi'

import { Link } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import '../styles/Welcome.css'
import AnimatedOrbitBackground from '../components/AnimatedOrbitBackground'
import WhyOrbit from '../components/WhyOrbit'
import '../styles/WhyOrbit.css'

const accessOptions = [
  {
    to: '/login',
    icon: FiLogIn,
    title: 'Advisor Login',
    description:
      'Sign in to access your dashboard, manage clients, and organize your daily workflows.',
    cta: 'Sign in to workspace',
  },
  {
    to: '/create-account',
    icon: FiUserPlus,
    title: 'Advisor Registration',
    description: 'Join Orbit and create your advisor account to get started with your workspace.',
    cta: 'Create an account',
  },
  {
    to: '/book-meeting',
    icon: FiCalendar,
    title: 'Public Booking',
    description:
      'Looking to connect with a financial advisor? Schedule a meeting without creating an account.',
    cta: 'Book a meeting',
  },
]

function Welcome() {
  return (
    <main className="welcome-page">
      {/* Background decoration */}
      <AnimatedOrbitBackground />
      {/* Main content */}
      <div className="welcome-container">
        {/* Hero section */}
        <section className="welcome-hero" aria-labelledby="welcome-title">
          <div className="welcome-logo-frame">
            <img src={orbitLogo} alt="Orbit logo" />
          </div>

          <span className="welcome-eyebrow">ADVISOR WORKSPACE PLATFORM</span>

          <h1 id="welcome-title">
            Your advisory practice,
            <span> all in one place.</span>
          </h1>

          <p className="welcome-intro">
            Welcome to Orbit. A centralized platform designed to simplify client management,
            organize meetings, and streamline everyday workflows for financial advisors.
          </p>
        </section>

        {/* Why Orbit section */}
        <WhyOrbit />

        {/* Access options */}
        <section className="welcome-access" aria-labelledby="access-title">
          <div className="welcome-section-heading">
            <h2 id="access-title">Get started with Orbit</h2>
            <p>Choose an option below to access the platform.</p>
          </div>

          <div className="welcome-options">
            {accessOptions.map(({ to, icon: Icon, title, description, cta }) => (
              <Link key={to} to={to} className="welcome-card">
                <div className="welcome-card-top">
                  <div className="welcome-card-icon">
                    <Icon aria-hidden="true" />
                  </div>

                  <span className="welcome-card-arrow">
                    <FiArrowRight aria-hidden="true" />
                  </span>
                </div>

                <h3>{title}</h3>

                <p>{description}</p>

                <div className="welcome-card-cta">
                  {cta}
                  <FiArrowRight aria-hidden="true" />
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="welcome-footer">
        <span>© {new Date().getFullYear()} Orbit. All rights reserved.</span>
        <span>Designed for better advisor-client relationships.</span>
      </footer>
    </main>
  )
}

export default Welcome
