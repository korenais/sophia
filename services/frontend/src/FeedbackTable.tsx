import {
  BugReport,
  Delete,
  DeleteSweep,
  Lightbulb,
  Person,
  Search,
  Visibility,
  Warning
} from '@mui/icons-material'
import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  InputAdornment,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography
} from '@mui/material'
import {
  DataGrid,
  GridActionsCellItem,
  GridColDef,
  GridRowParams
} from '@mui/x-data-grid'
import * as React from 'react'
import { useEffect, useState, useMemo } from 'react'

type Feedback = {
  id: number
  user_id: number
  message: string
  type: 'report' | 'suggestion'
  created_at: string
}

type User = {
  user_id: number
  intro_name: string | null
  intro_location: string | null
  intro_description: string | null
  intro_linkedin: string | null
  intro_hobbies_drivers: string | null
  intro_skills: string | null
  field_of_activity: string | null
  intro_birthday: string | null
  intro_image: string | null
  user_telegram_link: string | null
  state: string | null
  notifications_enabled: boolean | null
  matches_disabled: boolean | null
  finishedonboarding: boolean | null
}

// Forward declaration for the handlers
let handleViewDetails: (feedback: Feedback) => void
let handleDeleteFeedback: (feedback: Feedback) => void

const createColumns = (userMap: Map<number, User | null>): GridColDef<Feedback>[] => [
  {
    field: 'user_id',
    headerName: 'User',
    width: 200,
    renderCell: (params) => {
      const userId = params.value as number
      const isSystem = userId === 0
      
      if (isSystem) {
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar
              sx={{
                width: 24,
                height: 24,
                bgcolor: 'warning.main',
                color: 'white'
              }}
            >
              <Warning fontSize="small" />
            </Avatar>
            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
              System
            </Typography>
          </Box>
        )
      }
      
      const user = userMap.get(userId)
      const isDeleted = user === null && userMap.has(userId)
      const userName = user?.intro_name || `User ${userId}`
      
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar
            sx={{
              width: 24,
              height: 24,
              bgcolor: 'primary.light',
              color: 'white'
            }}
            src={user?.intro_image || undefined}
          >
            {!user?.intro_image && <Person fontSize="small" />}
          </Avatar>
          <Typography 
            variant="body2" 
            sx={{ 
              textDecoration: isDeleted ? 'line-through' : 'none',
              color: isDeleted ? 'text.secondary' : 'text.primary'
            }}
          >
            {userName}
          </Typography>
        </Box>
      )
    }
  },
  {
    field: 'type',
    headerName: 'Type',
    width: 120,
    renderCell: (params) => {
      const isReport = params.value === 'report'
      return (
        <Chip
          label={isReport ? 'Bug Report' : 'Suggestion'}
          size="small"
          color={isReport ? 'error' : 'info'}
          variant="outlined"
          icon={isReport ? <BugReport fontSize="small" /> : <Lightbulb fontSize="small" />}
        />
      )
    }
  },
  {
    field: 'message',
    headerName: 'Message',
    flex: 1,
    renderCell: (params) => (
      <Typography
        variant="body2"
        sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 300
        }}
      >
        {params.value}
      </Typography>
    )
  },
  {
    field: 'created_at',
    headerName: 'Created',
    width: 150,
    renderCell: (params) => (
      <Typography variant="body2">
        {new Date(params.value).toLocaleDateString()}
      </Typography>
    )
  },
  {
    field: 'actions',
    type: 'actions',
    headerName: 'Actions',
    width: 150,
    getActions: (params: GridRowParams) => [
      <GridActionsCellItem
        icon={<Visibility />}
        label="View Details"
        onClick={() => handleViewDetails(params.row)}
      />,
      <GridActionsCellItem
        icon={<Delete />}
        label="Delete"
        onClick={() => handleDeleteFeedback(params.row)}
        sx={{ color: 'error.main' }}
      />
    ]
  }
]

export const FeedbackTable: React.FC<{ apiBase?: string }> = ({ apiBase }) => {
  const base = apiBase || window.location.origin
  const [data, setData] = useState<Feedback[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [filterType, setFilterType] = useState<'all' | 'report' | 'suggestion'>('all')
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [feedbackToDelete, setFeedbackToDelete] = useState<Feedback | null>(null)
  const [bulkDeleteMenuAnchor, setBulkDeleteMenuAnchor] = useState<null | HTMLElement>(null)
  const [users, setUsers] = useState<Map<number, User | null>>(new Map())

  handleViewDetails = (feedback: Feedback) => {
    setSelectedFeedback(feedback)
    setDetailOpen(true)
  }

  handleDeleteFeedback = (feedback: Feedback) => {
    setFeedbackToDelete(feedback)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!feedbackToDelete) return

    try {
      const response = await fetch(`${base}/api/feedback/${feedbackToDelete.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Remove from local state
        setData(data.filter(item => item.id !== feedbackToDelete.id))
        setDeleteConfirmOpen(false)
        setFeedbackToDelete(null)
      } else {
        console.error('Failed to delete feedback')
      }
    } catch (error) {
      console.error('Error deleting feedback:', error)
    }
  }

  const handleBulkDelete = async (type: 'all' | 'report' | 'suggestion') => {
    try {
      let endpoint = `${base}/api/feedback`
      if (type !== 'all') {
        endpoint = `${base}/api/feedback/type/${type}`
      }

      const response = await fetch(endpoint, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Refresh data
        fetchFeedback()
        setBulkDeleteMenuAnchor(null)
      } else {
        console.error('Failed to delete feedback')
      }
    } catch (error) {
      console.error('Error deleting feedback:', error)
    }
  }

  const fetchUserInfo = async (userId: number): Promise<User | null> => {
    if (userId === 0) return null // System user, skip
    
    try {
      const resp = await fetch(`${base}/api/users/${userId}`)
      if (resp.ok) {
        const user: User = await resp.json()
        return user
      } else if (resp.status === 404) {
        // User not found (deleted)
        return null
      }
      return null
    } catch (e) {
      console.error(`Failed to load user ${userId}`, e)
      return null
    }
  }

  const fetchUsersForFeedback = async (feedbackList: Feedback[]) => {
    // Get unique user IDs (excluding system user with ID 0)
    const userIds = [...new Set(feedbackList.map(f => f.user_id).filter(id => id !== 0))]
    
    // Fetch user info for all unique user IDs
    const userPromises = userIds.map(userId => 
      fetchUserInfo(userId).then(user => ({ userId, user }))
    )
    
    const userResults = await Promise.all(userPromises)
    const newUserMap = new Map<number, User | null>()
    
    // Mark all fetched users (including null for deleted users)
    userResults.forEach(({ userId, user }) => {
      newUserMap.set(userId, user)
    })
    
    setUsers(newUserMap)
  }

  const fetchFeedback = async () => {
    try {
      setLoading(true)
      const resp = await fetch(`${base}/api/feedback`)
      const json: Feedback[] = await resp.json()
      setData(json)
      
      // Fetch user information for all feedback items
      await fetchUsersForFeedback(json)
    } catch (e) {
      console.error('Failed to load feedback', e)
      // Mock data for demonstration
      const mockData: Feedback[] = [
        {
          id: 1,
          user_id: 1541686636,
          message: "The bot sometimes doesn't respond to my messages. It seems to hang on certain commands.",
          type: 'report' as const,
          created_at: new Date().toISOString()
        },
        {
          id: 2,
          user_id: 999000111,
          message: "It would be great to have a feature to filter matches by location or interests.",
          type: 'suggestion' as const,
          created_at: new Date(Date.now() - 86400000).toISOString()
        }
      ]
      setData(mockData)
      await fetchUsersForFeedback(mockData)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFeedback()
  }, [base])

  // Set up automatic refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchFeedback()
    }, 30000) // Refresh every 30 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [base])

  const filteredData = data.filter(feedback => {
    const user = users.get(feedback.user_id)
    const userName = user?.intro_name || `User ${feedback.user_id}`
    const matchesSearch = feedback.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      feedback.user_id.toString().includes(searchTerm) ||
      (userName && userName.toLowerCase().includes(searchTerm.toLowerCase()))
    const matchesType = filterType === 'all' || feedback.type === filterType
    return matchesSearch && matchesType
  })

  const getTypeStats = () => {
    const stats = data.reduce((acc, feedback) => {
      acc[feedback.type] = (acc[feedback.type] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    return stats
  }

  const stats = getTypeStats()

  const columns = useMemo(() => createColumns(users), [users])

  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Feedback
              </Typography>
              <Typography variant="h4">
                {data.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Bug Reports
              </Typography>
              <Typography variant="h4" color="error.main">
                {stats.report || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Suggestions
              </Typography>
              <Typography variant="h4" color="info.main">
                {stats.suggestion || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Tabs
          value={filterType}
          onChange={(_, v) => setFilterType(v)}
        >
          <Tab label="All" value="all" />
          <Tab label="Bug Reports" value="report" />
          <Tab label="Suggestions" value="suggestion" />
        </Tabs>

        <Box>
          <Tooltip title="Bulk Delete Options">
            <IconButton
              onClick={(e) => setBulkDeleteMenuAnchor(e.currentTarget)}
              color="error"
              size="small"
            >
              <DeleteSweep />
            </IconButton>
          </Tooltip>

          <Menu
            anchorEl={bulkDeleteMenuAnchor}
            open={Boolean(bulkDeleteMenuAnchor)}
            onClose={() => setBulkDeleteMenuAnchor(null)}
          >
            <MenuItem onClick={() => handleBulkDelete('all')}>
              <ListItemIcon>
                <Warning color="error" />
              </ListItemIcon>
              <ListItemText primary="Delete All" />
            </MenuItem>
            <MenuItem onClick={() => handleBulkDelete('report')}>
              <ListItemIcon>
                <BugReport color="error" />
              </ListItemIcon>
              <ListItemText primary="Delete All Bug Reports" />
            </MenuItem>
            <MenuItem onClick={() => handleBulkDelete('suggestion')}>
              <ListItemIcon>
                <Lightbulb color="error" />
              </ListItemIcon>
              <ListItemText primary="Delete All Suggestions" />
            </MenuItem>
          </Menu>
        </Box>
      </Box>

      <TextField
        fullWidth
        placeholder="Search feedback by message, user name, or user ID..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 2 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
      />

      <Box sx={{ height: 500, width: '100%' }}>
        <DataGrid
          loading={loading}
          rows={filteredData}
          columns={columns}
          pageSizeOptions={[5, 10, 25]}
          pagination
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } }
          }}
        />
      </Box>

      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {selectedFeedback?.type === 'report' ?
              <BugReport color="error" /> :
              <Lightbulb color="info" />
            }
            <Typography variant="h6">
              {selectedFeedback?.type === 'report' ? 'Bug Report' : 'Feature Suggestion'}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedFeedback && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar
                          sx={{
                            bgcolor: selectedFeedback.user_id === 0 ? 'warning.main' : 'primary.light',
                            color: 'white'
                          }}
                        >
                          {selectedFeedback.user_id === 0 ? <Warning /> : <Person />}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2">Source</Typography>
                          {(() => {
                            const userId = selectedFeedback.user_id
                            const isSystem = userId === 0
                            const user = users.get(userId)
                            const isDeleted = user === null && users.has(userId)
                            const userName = user?.intro_name || `User ${userId}`
                            
                            return (
                              <Typography 
                                variant="h6" 
                                sx={{ 
                                  fontStyle: isSystem ? 'italic' : 'normal',
                                  textDecoration: isDeleted ? 'line-through' : 'none',
                                  color: isDeleted ? 'text.secondary' : 'text.primary'
                                }}
                              >
                                {isSystem ? 'System (Automated)' : userName}
                              </Typography>
                            )
                          })()}
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box>
                        <Typography variant="subtitle2">Type</Typography>
                        <Chip
                          label={selectedFeedback.type === 'report' ? 'Bug Report' : 'Suggestion'}
                          color={selectedFeedback.type === 'report' ? 'error' : 'info'}
                          variant="outlined"
                          icon={selectedFeedback.type === 'report' ? <BugReport /> : <Lightbulb />}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" gutterBottom>Message</Typography>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedFeedback.message}
                  </Typography>
                </CardContent>
              </Card>

              <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="subtitle2">Created:</Typography>
                <Typography variant="body2">
                  {new Date(selectedFeedback.created_at).toLocaleString()}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Warning color="error" />
            <Typography variant="h6">Confirm Delete</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this feedback?
          </Typography>
          {feedbackToDelete && (
            <Card variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                {feedbackToDelete.type === 'report' ? 'Bug Report' : 'Feature Suggestion'}
              </Typography>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {(() => {
                  const userId = feedbackToDelete.user_id
                  const isSystem = userId === 0
                  const user = users.get(userId)
                  const isDeleted = user === null && users.has(userId)
                  const userName = user?.intro_name || `User ${userId}`
                  
                  return isSystem ? 'System' : (
                    <span style={{ textDecoration: isDeleted ? 'line-through' : 'none' }}>
                      {userName} (ID: {userId})
                    </span>
                  )
                })()}
              </Typography>
              <Typography variant="body2">
                {feedbackToDelete.message.length > 100
                  ? `${feedbackToDelete.message.substring(0, 100)}...`
                  : feedbackToDelete.message
                }
              </Typography>
            </Card>
          )}
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={confirmDelete}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
