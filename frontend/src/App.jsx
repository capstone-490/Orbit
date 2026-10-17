import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AdvisorLayout from './components/dashboard/AdvisorLayout'
import Activity from './pages/Activity'
import AdvisorDashboard from './pages/AdvisorDashboard'
import AIReview from './pages/AIReview'
import Calendar from './pages/Calendar'
import Clients from './pages/Clients'
import Documents from './pages/Documents'
import FollowUps from './pages/FollowUps'
import Tasks from './pages/Tasks'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AdvisorLayout />}>
          <Route path="/" element={<AdvisorDashboard />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/follow-ups" element={<FollowUps />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/ai-review" element={<AIReview />} />
          <Route path="/activity" element={<Activity />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App