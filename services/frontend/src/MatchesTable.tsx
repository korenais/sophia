import * as React from 'react'
import { useEffect, useState } from 'react'
import { 
  DataGrid, 
  GridColDef, 
  GridActionsCellItem,
  GridRowParams
} from '@mui/x-data-grid'
import { 
  Box, 
  TextField, 
  InputAdornment, 
  Chip, 
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Avatar,
  Divider,
  Card,
  CardContent,
  Grid
} from '@mui/material'
import { Search, Visibility, Person, Schedule, CheckCircle, Cancel } from '@mui/icons-material'

type Meeting = {
  id: number
  user_1_id: number
  user1_name: string
  user_2_id: number
  user2_name: string
  status: string
  created_at: string
}

const columns: GridColDef<Meeting>[] = [
  { 
    field: 'user1_name', 
    headerName: 'User 1', 
    flex: 1,
    renderCell: (params) => (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Avatar 
          sx={{ 
            width: 32, 
            height: 32,
            bgcolor: 'primary.light',
            color: 'white'
          }}
        >
          <Person fontSize="small" />
        </Avatar>
        <Typography variant="body2">{params.value}</Typography>
      </Box>
    )
  },
  { 
    field: 'user2_name', 
    headerName: 'User 2', 
    flex: 1,
    renderCell: (params) => (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Avatar 
          sx={{ 
            width: 32, 
            height: 32,
            bgcolor: 'primary.light',
            color: 'white'
          }}
        >
          <Person fontSize="small" />
        </Avatar>
        <Typography variant="body2">{params.value}</Typography>
      </Box>
    )
  },
  { 
    field: 'status', 
    headerName: 'Status', 
    width: 120,
    renderCell: (params) => {
      const getStatusColor = (status: string) => {
        switch (status) {
          case 'new': return 'info'
          case 'confirmed': return 'success'
          case 'completed': return 'success'
          case 'cancelled': return 'error'
          default: return 'default'
        }
      }
      
      const getStatusIcon = (status: string) => {
        switch (status) {
          case 'confirmed':
          case 'completed':
            return <CheckCircle fontSize="small" />
          case 'cancelled':
            return <Cancel fontSize="small" />
          default:
            return <Schedule fontSize="small" />
        }
      }
      
      return (
        <Chip 
          label={params.value} 
          size="small" 
          color={getStatusColor(params.value)}
          variant="outlined"
          icon={getStatusIcon(params.value)}
        />
      )
    }
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
    width: 100,
    getActions: (params: GridRowParams) => [
      <GridActionsCellItem
        icon={<Visibility />}
        label="View Details"
        onClick={() => handleViewDetails(params.row)}
      />
    ]
  }
]

let handleViewDetails: (meeting: Meeting) => void

export const MatchesTable: React.FC<{ apiBase?: string }> = ({ apiBase }) => {
  const base = apiBase || window.location.origin
  const [data, setData] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  handleViewDetails = (meeting: Meeting) => {
    setSelectedMeeting(meeting)
    setDetailOpen(true)
  }

  // Function to fetch meetings data
  const fetchMeetings = async () => {
    try {
      setLoading(true)
      const resp = await fetch(`${base}/api/meetings`)
      const json: Meeting[] = await resp.json()
      setData(json)
    } catch (e) {
      console.error('Failed to load meetings', e)
    } finally {
      setLoading(false)
    }
  }

  // Initial data fetch
  useEffect(() => {
    fetchMeetings()
  }, [base])

  // Set up automatic refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchMeetings()
    }, 30000) // Refresh every 30 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [base])

  const filteredData = data.filter(meeting => 
    meeting.user1_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    meeting.user2_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    meeting.status.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getStatusStats = () => {
    const stats = data.reduce((acc, meeting) => {
      acc[meeting.status] = (acc[meeting.status] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    return stats
  }

  const stats = getStatusStats()

  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Matches
              </Typography>
              <Typography variant="h4">
                {data.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                New Matches
              </Typography>
              <Typography variant="h4" color="info.main">
                {stats.new || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Confirmed
              </Typography>
              <Typography variant="h4" color="success.main">
                {(stats.confirmed || 0) + (stats.completed || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Cancelled
              </Typography>
              <Typography variant="h4" color="error.main">
                {stats.cancelled || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TextField
        fullWidth
        placeholder="Search matches by user names or status..."
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
          <Typography variant="h6">Match Details</Typography>
        </DialogTitle>
        <DialogContent>
          {selectedMeeting && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                        <Avatar 
                          sx={{ 
                            width: 48, 
                            height: 48,
                            bgcolor: 'primary.light',
                            color: 'white'
                          }}
                        >
                          <Person />
                        </Avatar>
                        <Box>
                          <Typography variant="h6">{selectedMeeting.user1_name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {selectedMeeting.user_1_id}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                        <Avatar 
                          sx={{ 
                            width: 48, 
                            height: 48,
                            bgcolor: 'primary.light',
                            color: 'white'
                          }}
                        >
                          <Person />
                        </Avatar>
                        <Box>
                          <Typography variant="h6">{selectedMeeting.user2_name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {selectedMeeting.user_2_id}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
              
              <Divider sx={{ my: 3 }} />
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Typography variant="subtitle2">Status:</Typography>
                <Chip 
                  label={selectedMeeting.status} 
                  color={selectedMeeting.status === 'confirmed' || selectedMeeting.status === 'completed' ? 'success' : 'default'}
                  variant="outlined"
                />
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="subtitle2">Created:</Typography>
                <Typography variant="body2">
                  {new Date(selectedMeeting.created_at).toLocaleString()}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
