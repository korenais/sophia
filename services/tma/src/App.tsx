import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { getStartParam } from './lib/telegram'
import PeoplePage from './pages/PeoplePage'
import PersonPage from './pages/PersonPage'
import ProfilePage from './pages/ProfilePage'
import EditProfilePage from './pages/EditProfilePage'
import MatchPage from './pages/MatchPage'
import BottomNav from './components/BottomNav'

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
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to="/people" replace />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/people/:userId" element={<PersonPage />} />
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
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
