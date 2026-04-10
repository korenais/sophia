import { AppBar, Box, Button, Toolbar, Typography } from '@mui/material'
import CssBaseline from '@mui/material/CssBaseline'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider, useAuth } from './AuthContext'
import { FeedbackTable } from './FeedbackTable'
import { LoginPage } from './LoginPage'
import { MatchesTable } from './MatchesTable'
import { NotificationsTable } from './NotificationsTable'
import { PeopleTable } from './PeopleTable'
import { ThanksTable } from './ThanksTable'

const theme = createTheme()

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || window.location.origin

const AppContent: React.FC = () => {
  const { isAuthenticated, login, logout } = useAuth()

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Sophia Admin Dashboard
          </Typography>
          <Button color="inherit" onClick={logout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>
      <Box sx={{ flexGrow: 1, p: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2, fontWeight: 600 }}>
              Users
            </Typography>
          <PeopleTable apiBase={API_BASE} />
          </Box>
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2, fontWeight: 600 }}>
              Matches
            </Typography>
          <MatchesTable apiBase={API_BASE} />
          </Box>
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2, fontWeight: 600 }}>
              Reports and Suggestions
            </Typography>
          <FeedbackTable apiBase={API_BASE} />
          </Box>
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2, fontWeight: 600 }}>
              Thanks
            </Typography>
          <ThanksTable apiBase={API_BASE} />
          </Box>
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2, fontWeight: 600 }}>
              Notifications
            </Typography>
            <NotificationsTable apiBase={API_BASE} />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>
)


