import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  Paper,
  InputAdornment,
  IconButton
} from '@mui/material'
import { Visibility, VisibilityOff, Lock } from '@mui/icons-material'

interface LoginPageProps {
  onLogin: (password: string) => boolean
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }: LoginPageProps) => {
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    // Simulate a small delay for better UX
    await new Promise(resolve => setTimeout(resolve, 300))

    const isValid = onLogin(password)
    
    if (!isValid) {
      setError('Invalid password. Please try again.')
      setPassword('')
    }
    
    setIsLoading(false)
  }

  const handleTogglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: 2
        }}
      >
        <Paper
          elevation={24}
          sx={{
            width: '100%',
            maxWidth: 400,
            borderRadius: 3,
            overflow: 'hidden'
          }}
        >
          <Box
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              textAlign: 'center',
              py: 4,
              px: 3
            }}
          >
            <Lock sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h4" component="h1" fontWeight="bold">
              Sophia Admin
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.9, mt: 1 }}>
              Enter your password to access the dashboard
            </Typography>
          </Box>

          <CardContent sx={{ p: 4 }}>
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                variant="outlined"
                margin="normal"
                required
                autoFocus
                disabled={isLoading}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={handleTogglePasswordVisibility}
                        edge="end"
                        disabled={isLoading}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2,
                  }
                }}
              />

              {error && (
                <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
                  {error}
                </Alert>
              )}

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={isLoading || !password.trim()}
                sx={{
                  mt: 3,
                  mb: 2,
                  py: 1.5,
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                  },
                  '&:disabled': {
                    background: '#e0e0e0',
                    color: '#9e9e9e'
                  }
                }}
              >
                {isLoading ? 'Signing In...' : 'Sign In'}
              </Button>
            </form>
          </CardContent>
        </Paper>
      </Box>
    </Container>
  )
}
