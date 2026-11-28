// import { lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import DevFeatureFlagBar from './components/DevFeatureFlagBar'
// import { FlaggedView } from './components/FlaggedView'
import AdvisorLayout from './components/dashboard/AdvisorLayout'
import { FeatureFlagsProvider } from './context/FeatureFlagsContext'

import Activity from './pages/Activity'
import AdvisorDashboard from './pages/AdvisorDashboard'
import AIReview from './pages/AIReview'
import BookMeeting from './pages/BookMeeting'
import Calendar from './pages/Calendar'
import ClientInfo from './pages/ClientInfo'
import Clients from './pages/Clients'
import CreateAccount from './pages/CreateAccount'
import Documents from './pages/Documents'
import FollowUps from './pages/FollowUps'
import ForgotPassword from './pages/ForgotPassword'
import Login from './pages/Login'
import ResetPassword from './pages/ResetPassword'
import Tasks from './pages/Tasks'
import Welcome from './pages/Welcome'

// const LoginV2 = lazy(() => import('./v2/pages/Login'))

function App() {
  return (
    <FeatureFlagsProvider>
      <BrowserRouter>
        <Routes>
          {/* <Route path="/login" element={<FlaggedView flag="use_v2_workspace" v1={Login} v2={LoginV2} />}/> */}
          <Route path="/" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="/book-meeting" element={<BookMeeting />} />
          <Route element={<AdvisorLayout />}>
            <Route path="/dashboard" element={<AdvisorDashboard />} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/clients/:clientId" element={<ClientInfo />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/follow-ups" element={<FollowUps />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/ai-review" element={<AIReview />} />
            <Route path="/activity" element={<Activity />} />
          </Route>
        </Routes>
        {import.meta.env.DEV && <DevFeatureFlagBar />}
      </BrowserRouter>
    </FeatureFlagsProvider>
  )
}
export default App
