import {
  FiCalendar,
  FiCheckSquare,
  FiClock,
  FiCpu,
  FiFolder,
  FiLink,
  FiTrendingUp,
  FiUserCheck,
  FiUsers,
} from 'react-icons/fi'
import '../styles/WhyOrbit.css'

const features = [
  {
    icon: FiUsers,
    title: 'Client management',
    description: 'Profiles, goals, financial snapshots, and notes in one client dossier.',
  },
  {
    icon: FiTrendingUp,
    title: 'Financial education',
    description: 'Track each client from introduction through to plan presentation.',
  },
  {
    icon: FiCalendar,
    title: 'Meetings',
    description: 'Manage availability and appointments, linked to client profiles.',
  },
  {
    icon: FiCheckSquare,
    title: 'Tasks and follow-ups',
    description: 'Stay on top of deadlines and client actions so nothing slips.',
  },
  {
    icon: FiFolder,
    title: 'Documents',
    description: 'Organize client files and spot missing documents at a glance.',
  },
  {
    icon: FiCpu,
    title: 'AI assistance',
    description: 'Summaries, follow-up drafts, and suggested next steps from client context.',
  },
]

const principles = [
  {
    icon: FiLink,
    title: 'Connected to your work',
    description: 'AI draws on client records, meetings, and documents, not a blank prompt.',
  },
  {
    icon: FiUserCheck,
    title: 'Advisor approval first',
    description: 'Review and edit every AI-generated summary or message before it goes out.',
  },
  {
    icon: FiClock,
    title: 'Clear activity history',
    description: 'Keep a record of updates, completed meetings, and approvals.',
  },
]

function WhyOrbit() {
  return (
    <section className="why-orbit" aria-labelledby="why-orbit-title">
      <header className="why-orbit-heading">
        <span className="welcome-eyebrow">OUR APP'S MAIN FEATURES</span>
      </header>

      <ul className="why-orbit-features">
        {features.map(({ icon: Icon, title, description }) => (
          <li key={title} className="why-orbit-feature">
            <span className="why-orbit-icon">
              <Icon aria-hidden="true" />
            </span>
            <div>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
          </li>
        ))}
      </ul>

      <div className="why-orbit-principles">
        <p className="why-orbit-principles-label">AI that works the way advisors do</p>
        <ul>
          {principles.map(({ icon: Icon, title, description }) => (
            <li key={title}>
              <Icon aria-hidden="true" />
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export default WhyOrbit
