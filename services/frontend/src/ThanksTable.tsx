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
  Card,
  CardContent,
  Grid
} from '@mui/material'
import { Search, Visibility, Star, TrendingUp, History } from '@mui/icons-material'

interface ThanksStats {
  receiver_username: string
  total: number
}

interface RecentThanks {
  id: number
  sender_username: string
  receiver_username: string
  created_at: string
}

const columns: GridColDef[] = [
  {
    field: 'receiver_username',
    headerName: 'User',
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
          {params.value.charAt(0).toUpperCase()}
        </Avatar>
        <Typography variant="body2">@{params.value}</Typography>
      </Box>
    )
  },
  {
    field: 'total',
    headerName: 'Thanks Count',
    width: 150,
    renderCell: (params) => (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Star sx={{ color: 'gold', fontSize: 16 }} />
        <Typography variant="body2" fontWeight="bold">
          {params.value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          ({'⭐️'.repeat(Math.min(params.value, 3))})
        </Typography>
      </Box>
    )
  }
]

export const ThanksTable: React.FC<{ apiBase?: string }> = ({ apiBase }) => {
  const base = apiBase || window.location.origin
  const [thanksStats, setThanksStats] = useState<ThanksStats[]>([])
  const [recentThanks, setRecentThanks] = useState<RecentThanks[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedThanks, setSelectedThanks] = useState<ThanksStats | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    fetchThanksData()
  }, [base])

  // Set up automatic refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchThanksData()
    }, 30000) // Refresh every 30 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [base])

  const fetchThanksData = async () => {
    try {
      setLoading(true)
      const [statsResponse, recentResponse] = await Promise.all([
        fetch(`${base}/api/thanks/stats`),
        fetch(`${base}/api/thanks/recent?limit=50`)
      ])
      
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setThanksStats(statsData)
      }
      
      if (recentResponse.ok) {
        const recentData = await recentResponse.json()
        setRecentThanks(recentData)
      }
    } catch (error) {
      console.error('Error fetching thanks data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetails = (thanks: ThanksStats) => {
    setSelectedThanks(thanks)
    setDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setDialogOpen(false)
    setSelectedThanks(null)
  }

  const filteredData = thanksStats.filter(thanks =>
    thanks.receiver_username.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const totalThanks = thanksStats.reduce((sum, thanks) => sum + thanks.total, 0)
  const totalUsers = thanksStats.length
  const avgThanks = totalUsers > 0 ? Math.round(totalThanks / totalUsers * 10) / 10 : 0
  const topUser = thanksStats.length > 0 ? thanksStats[0] : null

  const selectedUserRecentThanks = selectedThanks 
    ? recentThanks.filter(thanks => thanks.receiver_username === selectedThanks.receiver_username)
    : []

  return (
    <Box>
      {/* Statistics Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Star sx={{ color: 'gold' }} />
                <Typography variant="h6">Total Thanks</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {totalThanks}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUp sx={{ color: 'green' }} />
                <Typography variant="h6">Active Users</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {totalUsers}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Star sx={{ color: 'orange' }} />
                <Typography variant="h6">Avg Thanks</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {avgThanks}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Star sx={{ color: 'purple' }} />
                <Typography variant="h6">Top User</Typography>
              </Box>
              <Typography variant="h6" color="primary">
                {topUser ? `@${topUser.receiver_username}` : 'None'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {topUser ? `${topUser.total} thanks` : ''}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TextField
        fullWidth
        placeholder="Search users by username..."
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
          getRowId={(row) => row.receiver_username}
          onRowClick={(params) => handleViewDetails(params.row)}
          sx={{
            '& .MuiDataGrid-row:hover': {
              cursor: 'pointer'
            }
          }}
        />
      </Box>

      {/* Details Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar 
              sx={{ 
                bgcolor: 'primary.light',
                color: 'white'
              }}
            >
              {selectedThanks?.receiver_username.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="h6">@{selectedThanks?.receiver_username}</Typography>
              <Typography variant="body2" color="text.secondary">
                {selectedThanks?.total} total thanks
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <History />
            Recent Thanks Received
          </Typography>
          {selectedUserRecentThanks.length > 0 ? (
            <Box>
              {selectedUserRecentThanks.slice(0, 10).map((thanks) => (
                <Box key={thanks.id} sx={{ mb: 1, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="body2">
                    <strong>@{thanks.sender_username}</strong> thanked <strong>@{thanks.receiver_username}</strong>
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(thanks.created_at).toLocaleString()}
                  </Typography>
                </Box>
              ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No recent thanks found.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
