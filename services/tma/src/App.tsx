import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { getStartParam } from './lib/telegram'
import PeoplePage from './pages/PeoplePage'
import PersonPage from './pages/PersonPage'
import ProfilePage from './pages/ProfilePage'
import EditProfilePage from './pages/EditProfilePage'
import MatchPage from './pages/MatchPage'
import BottomNav from './components/BottomNav'
import TopBar from './components/TopBar'
import EventsPage from './pages/EventsPage'
import RequestsPage from './pages/RequestsPage'
import ServicesPage from './pages/ServicesPage'
import MatchHubPage from './pages/MatchHubPage'
import { HOME_ROUTE } from './lib/routes'

const routerBase =
  import.meta.env.BASE_URL === '/'
    ? '/'
    : import.meta.env.BASE_URL.replace(/\/$/, '')

function AppRoutes() {
  const navigate = useNavigate()

  useEffect(() => {
    const param = getStartParam()
    if (param?.startsWith('match_')) {
      const meetingId = param.replace('match_', '')
      navigate(`/match/${meetingId}`, { replace: true })
    }
  }, [])

  return (
    <div className="flex flex-col h-full bg-bg">
      <TopBar />
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to={HOME_ROUTE} replace />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/people/:userId" element={<PersonPage />} />
          <Route path="/matches" element={<MatchHubPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/requests" element={<RequestsPage />} />
          <Route path="/services" element={<ServicesPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/profile/edit" element={<EditProfilePage />} />
          <Route path="/match/:meetingId" element={<MatchPage />} />
        </Routes>
      </div>
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter basename={routerBase}>
      <AppRoutes />
    </BrowserRouter>
  )
}
