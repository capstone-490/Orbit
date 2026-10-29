import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AdvisorLayout from './components/dashboard/AdvisorLayout'
import Activity from './pages/Activity'
import AdvisorDashboard from './pages/AdvisorDashboard'
import AIReview from './pages/AIReview'
import BookMeeting from './pages/BookMeeting'
import Calendar from './pages/Calendar'
import Clients from './pages/Clients'
import CreateAccount from './pages/CreateAccount'
import Documents from './pages/Documents'
import FollowUps from './pages/FollowUps'
import Login from './pages/Login'
import Tasks from './pages/Tasks'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/create-account" element={<CreateAccount />} />
        <Route path="/book-meeting" element={<BookMeeting />} />
        <Route element={<AdvisorLayout />}>
          <Route path="/dashboard" element={<AdvisorDashboard />} />
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
