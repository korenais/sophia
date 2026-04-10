import { Add, Close, Delete, Edit, Link, LocationOn, NotificationsOff, Person, Search, Visibility } from '@mui/icons-material'
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  Snackbar,
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
import { useEffect, useMemo, useState } from 'react'
import UserForm from './UserForm'

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

type Person = {
  id: number
  name: string
  location: string
  notifications_enabled?: boolean
  matches_disabled?: boolean
  finishedonboarding?: boolean
  description: string
  linkedin: string
  hobbies_drivers: string
  skills: string
  field_of_activity: string
  birthday: string
  image: string | null
  telegram_link: string | null
  status: string
  groups?: string[]  // Group names
}

// Columns definition - no need for groups map anymore
const columns: GridColDef<Person>[] = [
  {
    field: 'name',
    headerName: 'Name',
    flex: 1,
    renderCell: (params) => {
      // Protect against arrays - MUI DataGrid should never pass arrays here
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      const hasTelegram = params.row.telegram_link && params.row.telegram_link.trim() !== ''
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar
            sx={{
              width: 32,
              height: 32,
              bgcolor: 'primary.light',
              color: 'white'
            }}
            src={params.row.image || undefined}
          >
            {!params.row.image && <Person fontSize="small" />}
          </Avatar>
          <Tooltip title={!hasTelegram ? "No Telegram link - cannot send messages" : ""}>
            <Typography 
              variant="body2"
              sx={{
                color: !hasTelegram ? 'error.main' : 'inherit'
              }}
            >
              {value}
            </Typography>
          </Tooltip>
        </Box>
      )
    }
  },
  {
    field: 'location',
    headerName: 'Location',
    flex: 1,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <LocationOn fontSize="small" color="action" />
          <Typography variant="body2">{value}</Typography>
        </Box>
      )
    }
  },
  {
    field: 'linkedin',
    headerName: 'LinkedIn',
    flex: 1,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Link fontSize="small" color="action" />
          <Typography variant="body2" sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 200
          }}>
            {value}
          </Typography>
        </Box>
      )
    }
  },
  {
    field: 'hobbies_drivers',
    headerName: 'Hobbies & Drivers',
    flex: 1,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Typography variant="body2" sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 200
        }}>
          {value}
        </Typography>
      )
    }
  },
  {
    field: 'skills',
    headerName: 'Skills',
    flex: 1,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Typography variant="body2" sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 200
        }}>
          {value}
        </Typography>
      )
    }
  },
  {
    field: 'field_of_activity',
    headerName: 'Field of Activity',
    flex: 1,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Typography variant="body2" sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 200
        }}>
          {value}
        </Typography>
      )
    }
  },
  {
    field: 'birthday',
    headerName: 'Birthday',
    width: 120,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Typography variant="body2">
          {value}
        </Typography>
      )
    }
  },
  {
    field: 'status',
    headerName: 'Status',
    width: 120,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? String(params.value) : params.value
      return (
        <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
          {value}
        </Typography>
      )
    }
  },
  {
    field: 'notifications_enabled',
    headerName: 'Notifications',
    width: 130,
    sortable: true,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? false : params.value
      return (
        <Typography 
          variant="body2" 
          sx={{ 
            fontSize: '0.875rem',
            color: value ? 'inherit' : 'error.main'
          }}
        >
          {value ? 'ON' : 'OFF'}
        </Typography>
      )
    }
  },
  {
    field: 'matches_disabled',
    headerName: 'Matches',
    width: 110,
    sortable: true,
    renderCell: (params) => {
      const value = Array.isArray(params.value) ? false : params.value
      const isEnabled = !value // matches_disabled is inverted logic
      return (
        <Typography 
          variant="body2" 
          sx={{ 
            fontSize: '0.875rem',
            color: isEnabled ? 'inherit' : 'error.main'
          }}
        >
          {isEnabled ? 'ON' : 'OFF'}
        </Typography>
      )
    }
  },
  {
    field: 'finishedonboarding',
    headerName: 'Registration',
    width: 130,
    sortable: true,
    renderCell: (params) => {
      // Protect against arrays first
      const rawValue = Array.isArray(params.value) ? false : params.value
      
      // Handle boolean values correctly - false should be false, not converted to true
      let value = false
      if (rawValue === true || rawValue === 'true' || rawValue === 1) {
        value = true
      } else if (rawValue === false || rawValue === 'false' || rawValue === 0) {
        value = false
      } else if (rawValue !== null && rawValue !== undefined) {
        // For any other truthy value, convert to boolean
        value = Boolean(rawValue)
      } else {
        // Default to true if null/undefined
        value = true
      }
      return (
        <Typography 
          variant="body2" 
          sx={{ 
            fontSize: '0.875rem',
            color: value ? 'inherit' : 'error.main'
          }}
        >
          {value ? 'ON' : 'OFF'}
        </Typography>
      )
    }
  },
  {
    field: 'groups_str',
    headerName: 'Groups',
    flex: 1,
    sortable: true,
    renderCell: (params: any) => {
      try {
        // Protect against arrays first
        const groupsStr = Array.isArray(params.value) ? String(params.value) : (params.value || '')
        
        if (!groupsStr || typeof groupsStr !== 'string' || groupsStr.trim() === '') {
          return <Typography variant="body2"> </Typography>
        }
        
        // Split by comma - split always returns array
        const splitResult = groupsStr.split(',')
        if (!Array.isArray(splitResult)) {
          return <Typography variant="body2"> </Typography>
        }
        
        // Use for loop instead of map to avoid any issues
        const validGroups: string[] = []
        for (let i = 0; i < splitResult.length; i++) {
          const g = splitResult[i]
          if (g != null && typeof g === 'string') {
            const trimmed = g.trim()
            if (trimmed !== '') {
              validGroups.push(trimmed)
            }
          }
        }
        
        if (validGroups.length === 0) {
          return <Typography variant="body2"> </Typography>
        }
        
        // Display groups as comma-separated text for compact display
        const groupsText = validGroups.join(', ')
        
        return (
          <Typography 
            variant="body2" 
            sx={{ 
              fontSize: '0.875rem',
              lineHeight: 1.5,
              wordBreak: 'break-word',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical'
            }}
            title={groupsText} // Show full text on hover
          >
            {groupsText}
          </Typography>
        )
      } catch (error) {
        console.error('[ERROR] renderCell groups_str error:', error, params)
        return <Typography variant="body2"> </Typography>
      }
    }
  },
  {
    field: 'actions',
    type: 'actions',
    headerName: 'Actions',
    width: 150,
    getActions: (params: GridRowParams) => [
      <GridActionsCellItem
        icon={<Visibility />}
        label="View Profile"
        onClick={() => handleViewProfile(params.row)}
      />,
      <GridActionsCellItem
        icon={<Edit />}
        label="Edit User"
        onClick={() => handleEditUser(params.row)}
      />,
      <GridActionsCellItem
        icon={<Delete />}
        label="Delete User"
        onClick={() => handleDeleteUser(params.row)}
        showInMenu
      />
    ]
  }
]

let handleViewProfile: (user: Person) => void
let handleEditUser: (user: Person) => void
let handleDeleteUser: (user: Person) => void
let handleCreateUser: () => void

export const PeopleTable: React.FC<{ rows?: Person[]; apiBase?: string }> = ({ rows, apiBase }) => {
  const base = apiBase || window.location.origin
  const [data, setData] = useState<Person[]>(rows || [])
  const [loading, setLoading] = useState(!rows)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState<Person | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingUser, setEditingUser] = useState<Person | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [userToDelete, setUserToDelete] = useState<Person | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  handleViewProfile = (user: Person) => {
    // Get groups array from _groups_array if it exists
    const userWithGroups = { ...user }
    const groupsArray = (user as any)._groups_array
    if (groupsArray && Array.isArray(groupsArray)) {
      (userWithGroups as any).groups = groupsArray
    }
    setSelectedUser(userWithGroups)
    setDetailOpen(true)
  }

  handleEditUser = async (user: Person) => {
    // Fetch fresh user data from API to ensure we have the latest information
    try {
      const resp = await fetch(`${base}/api/users/${user.id}`)
      if (resp.ok) {
        const freshUser: User = await resp.json()
        // Map API User to Person format
        const freshPerson: Person = {
          id: freshUser.user_id,
          name: freshUser.intro_name || 'Anonymous',
          location: freshUser.intro_location || 'Not specified',
          description: freshUser.intro_description || 'No description',
          linkedin: freshUser.intro_linkedin || '',
          hobbies_drivers: freshUser.intro_hobbies_drivers || 'Not specified',
          skills: freshUser.intro_skills || 'Not specified',
          field_of_activity: freshUser.field_of_activity || 'Not specified',
          birthday: freshUser.intro_birthday ? String(freshUser.intro_birthday) : 'Not specified',
          image: freshUser.intro_image || null,
          telegram_link: freshUser.user_telegram_link || null,
          status: freshUser.state || 'UNKNOWN',
          notifications_enabled: freshUser.notifications_enabled !== null ? freshUser.notifications_enabled : true,
          matches_disabled: freshUser.matches_disabled !== null ? freshUser.matches_disabled : false,
          finishedonboarding: freshUser.finishedonboarding !== null && freshUser.finishedonboarding !== undefined ? freshUser.finishedonboarding === true : true,
        }
        setEditingUser(freshPerson)
      } else {
        // Fallback to cached data if API call fails
        setEditingUser(user)
      }
    } catch (error) {
      console.error('Failed to fetch fresh user data:', error)
      // Fallback to cached data if API call fails
      setEditingUser(user)
    }
    setFormMode('edit')
    setFormOpen(true)
  }

  handleDeleteUser = (user: Person) => {
    setUserToDelete(user)
    setDeleteDialogOpen(true)
  }

  handleCreateUser = () => {
    setEditingUser(null)
    setFormMode('create')
    setFormOpen(true)
  }

  // Function to fetch users data
  const fetchUsers = async () => {
    try {
      setLoading(true)
      const resp = await fetch(`${base}/api/users`)
      const json: User[] = await resp.json()
      
      // Fetch groups for all users in parallel
      const usersWithGroups = await Promise.all(
        json.map(async (u) => {
          try {
            const groupsResp = await fetch(`${base}/api/users/${u.user_id}/groups`)
            const groupsData = groupsResp.ok ? await groupsResp.json() : []
            
            // Ensure groups is always an array
            const groups = Array.isArray(groupsData) ? groupsData : []
            
            // Safely map groups to names, filtering out invalid entries
            let groupNames: string[] = []
            if (Array.isArray(groups)) {
              const filtered = groups.filter((g: any) => {
                return g && typeof g === 'object' && typeof g.name === 'string'
              })
              
              groupNames = filtered.map((g: { name: string }) => g.name)
            } else {
              console.error(`User ${u.user_id} groups is not an array!`, groups)
            }
            
            return {
              ...u,
              groups: groupNames
            }
          } catch (error) {
            console.error(`User ${u.user_id} error fetching groups:`, error)
            return { ...u, groups: [] }
          }
        })
      )
      
      // Map users to Person format - DO NOT include groups array in data
      // Also ensure NO arrays are in the data object
      const mapped: Person[] = usersWithGroups.map((u) => {
        // Get groups as array for later use (but don't put it in Person object)
        const userGroups = (u as any).groups || []
        const groupsArray = Array.isArray(userGroups) ? userGroups : []
        
        // Convert groups array to comma-separated string for DataGrid
        // This prevents MUI from trying to process it as an array
        let groupsStr = ''
        if (Array.isArray(groupsArray) && groupsArray.length > 0) {
          const validGroups: string[] = []
          for (let i = 0; i < groupsArray.length; i++) {
            const g = groupsArray[i]
            if (g != null && typeof g === 'string' && g.trim() !== '') {
              validGroups.push(g.trim())
            }
          }
          groupsStr = validGroups.join(',')
        }
        
        // Create person WITHOUT groups array - only string
        const person: any = {
          id: u.user_id,
          name: u.intro_name || 'Anonymous',
          location: u.intro_location || 'Not specified',
          description: u.intro_description || 'No description',
          linkedin: u.intro_linkedin || '',
          hobbies_drivers: u.intro_hobbies_drivers || 'Not specified',
          skills: u.intro_skills || 'Not specified',
          field_of_activity: u.field_of_activity || 'Not specified',
          birthday: u.intro_birthday ? String(u.intro_birthday) : 'Not specified',
          image: u.intro_image || null,
          telegram_link: u.user_telegram_link || null,
          status: u.state || 'UNKNOWN',
          notifications_enabled: u.notifications_enabled !== null ? u.notifications_enabled : true,
          matches_disabled: u.matches_disabled !== null ? u.matches_disabled : false,
          finishedonboarding: u.finishedonboarding === true ? true : (u.finishedonboarding === false ? false : true),
          // DO NOT include groups array here - it causes MUI DataGrid to try to process it
          groups_str: groupsStr || '', // Only string, never array
        }
        
        // Store groups array separately for detail view (not in Person object)
        // Use a symbol or special property name to avoid MUI DataGrid processing it
        Object.defineProperty(person, '_groups_array', {
          value: groupsArray,
          enumerable: false, // This prevents MUI DataGrid from seeing it
          writable: true,
          configurable: true
        })
        
        // Final check: ensure NO arrays in person object (except non-enumerable _groups_array)
        for (const key in person) {
          if (Array.isArray(person[key as keyof typeof person])) {
            console.error(`[ERROR] Found array in person data at key: ${key}`, person[key])
            // Convert array to string to prevent MUI DataGrid issues
            ;(person as any)[key] = String((person as any)[key])
          }
        }
        
        return person
      })
      
      setData(mapped)
    } catch (e) {
      console.error('Failed to load users', e)
    } finally {
      setLoading(false)
    }
  }

  // Function to fetch users data and return it
  const fetchUsersAndReturnData = async (): Promise<Person[]> => {
    try {
      const resp = await fetch(`${base}/api/users`)
      const json: User[] = await resp.json()
      const mapped: Person[] = json.map((u) => ({
        id: u.user_id,
        name: u.intro_name || 'Anonymous',
        location: u.intro_location || 'Not specified',
        description: u.intro_description || 'No description',
        linkedin: u.intro_linkedin || '',
        hobbies_drivers: u.intro_hobbies_drivers || 'Not specified',
        skills: u.intro_skills || 'Not specified',
        field_of_activity: u.field_of_activity || 'Not specified',
        birthday: u.intro_birthday ? String(u.intro_birthday) : 'Not specified',
        image: u.intro_image || null,
        telegram_link: u.user_telegram_link || null,
        status: u.state || 'UNKNOWN',
        notifications_enabled: u.notifications_enabled !== null ? u.notifications_enabled : true,
        matches_disabled: u.matches_disabled !== null ? u.matches_disabled : false,
        finishedonboarding: u.finishedonboarding === true ? true : (u.finishedonboarding === false ? false : true),
      }))
      setData(mapped)
      return mapped
    } catch (e) {
      console.error('Failed to load users', e)
      return []
    }
  }

  // Initial data fetch
  useEffect(() => {
    // Always fetch users, even if rows are provided (to ensure fresh data)
    fetchUsers()
  }, [base])

  // Set up automatic refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchUsers()
    }, 30000) // Refresh every 30 seconds

    // Cleanup interval on component unmount
    return () => {
      clearInterval(interval)
    }
  }, [base])

  const handleSaveUser = async (userData: Partial<User>) => {
    try {

      if (formMode === 'create') {
        // Remove user_id from creation data since API will auto-generate it
        const { user_id, ...createData } = userData
        const response = await fetch(`${base}/api/users`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(createData),
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error('Create user error:', response.status, errorText)

          if (response.status === 0 || !navigator.onLine) {
            throw new Error('API server is not available. Please check if the server is running.')
          } else if (response.status >= 500) {
            throw new Error(`Server error (${response.status}): ${errorText}`)
          } else if (response.status >= 400) {
            throw new Error(`Request error (${response.status}): ${errorText}`)
          } else {
            throw new Error(`Failed to create user: ${response.status} ${errorText}`)
          }
        }

        setSuccessMessage('User created successfully!')
      } else {
        const { user_id, ...updateData } = userData
        const response = await fetch(`${base}/api/users/${user_id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updateData),
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error('Update user error:', response.status, errorText)

          if (response.status === 404) {
            // User not found - might be due to user_id change, try to find by name and telegram link
            const resp = await fetch(`${base}/api/users`)
            if (resp.ok) {
              const json: User[] = await resp.json()
              const foundUser = json.find(u =>
                u.intro_name === userData.intro_name &&
                u.user_telegram_link === userData.user_telegram_link
              )
              if (foundUser) {
                // Retry with the correct user_id
                const { user_id, ...updateData } = { ...userData, user_id: foundUser.user_id }
                const retryResponse = await fetch(`${base}/api/users/${foundUser.user_id}`, {
                  method: 'PUT',
                  headers: {
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify(updateData),
                })
                if (retryResponse.ok) {
                  setSuccessMessage('User updated successfully!')
                  // Refresh the user list with groups data
                  await fetchUsers()

                  // Update editingUser with the fresh data
                  if (editingUser && formMode === 'edit') {
                    // Find updated user in the refreshed data
                    const updatedUser = data.find(u =>
                      u.id === editingUser.id
                    )
                    if (updatedUser) {
                      setEditingUser(updatedUser)
                    }
                  }
                  return
                }
              }
            }
            throw new Error('User not found. The user may have been deleted or the user ID has changed.')
          } else if (response.status === 0 || !navigator.onLine) {
            throw new Error('API server is not available. Please check if the server is running.')
          } else if (response.status >= 500) {
            throw new Error(`Server error (${response.status}): ${errorText}`)
          } else if (response.status >= 400) {
            throw new Error(`Request error (${response.status}): ${errorText}`)
          } else {
            throw new Error(`Failed to update user: ${response.status} ${errorText}`)
          }
        }

        setSuccessMessage('User updated successfully!')
      }

      // Refresh the user list with groups data
      await fetchUsers()

      // Update editingUser if we're currently editing this user
      if (editingUser && formMode === 'edit') {
        // Find updated user in the refreshed data
        const updatedUser = data.find(u =>
          u.id === editingUser.id
        )
        if (updatedUser) {
          setEditingUser(updatedUser)
        }
      }

    } catch (error) {
      console.error('Error saving user:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred'
      console.error('Error details:', errorMsg)
      setErrorMessage(errorMsg)
      throw error
    }
  }

  const handleConfirmDelete = async () => {
    if (!userToDelete) return

    try {
      const response = await fetch(`${base}/api/users/${userToDelete.id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        if (response.status === 404) {
          // User already deleted - just refresh the data
          await fetchUsers()
          setDeleteDialogOpen(false)
          setUserToDelete(null)
          return
        }
        throw new Error(errorData.detail || 'Failed to delete user')
      }

      // Refresh data to ensure consistency
      await fetchUsers()
      setDeleteDialogOpen(false)
      setUserToDelete(null)
    } catch (error) {
      console.error('Error deleting user:', error)
      alert('Failed to delete user. Please try again.')
    }
  }

  const filteredData = data.filter(user =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <TextField
          placeholder="Search users by name, location, or description..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ flexGrow: 1, mr: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleCreateUser}
        >
          Add User
        </Button>
      </Box>

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

      <Dialog
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        maxWidth="md"
        fullWidth
        disableRestoreFocus
        disableAutoFocus
        disableEnforceFocus
        PaperProps={{
          sx: {
            maxHeight: '90vh',
            height: 'auto'
          }
        }}
      >
        <DialogTitle sx={{ pb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
            <Avatar
              sx={{
                width: 48,
                height: 48,
                bgcolor: 'primary.main',
                color: 'white'
              }}
              src={selectedUser?.image || undefined}
            >
              {!selectedUser?.image && <Person sx={{ fontSize: 24 }} />}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, wordBreak: 'break-word' }}>
                {selectedUser?.name}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                <LocationOn fontSize="small" color="primary" />
                <Typography variant="body2" sx={{ color: 'text.secondary', wordBreak: 'break-word' }}>
                  {selectedUser?.location}
                </Typography>
                <Chip
                  label={selectedUser?.status}
                  size="small"
                  color={selectedUser?.status === 'ACTIVE' ? 'success' : 'default'}
                  sx={{ fontWeight: 500, ml: 1 }}
                />
                {selectedUser?.notifications_enabled === false && (
                  <Tooltip title="Notifications disabled">
                    <Chip
                      icon={<NotificationsOff />}
                      label="Notifications Off"
                      size="small"
                      color="warning"
                      variant="outlined"
                      sx={{ fontWeight: 500, ml: 1 }}
                    />
                  </Tooltip>
                )}
              </Box>
            </Box>
          </Box>
          <IconButton
            aria-label="close"
            onClick={() => setDetailOpen(false)}
            sx={{
              color: (theme) => theme.palette.grey[500],
              ml: 2
            }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ pt: 1, overflow: 'visible' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Status Settings */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.primary' }}>
                Status Settings
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1.5 }}>
                {/* Notifications */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Notifications
                  </Typography>
                  <Chip
                    label={selectedUser?.notifications_enabled !== false ? 'ON' : 'OFF'}
                    size="small"
                    color={selectedUser?.notifications_enabled !== false ? 'success' : 'default'}
                    variant="outlined"
                  />
                </Box>

                {/* Matches */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Matches
                  </Typography>
                  <Chip
                    label={selectedUser?.matches_disabled === true ? 'OFF' : 'ON'}
                    size="small"
                    color={selectedUser?.matches_disabled === true ? 'default' : 'success'}
                    variant="outlined"
                  />
                </Box>

                {/* Registration */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Registration
                  </Typography>
                  <Chip
                    label={selectedUser?.finishedonboarding !== false ? 'ON' : 'OFF'}
                    size="small"
                    color={selectedUser?.finishedonboarding !== false ? 'success' : 'default'}
                    variant="outlined"
                  />
                </Box>
              </Box>
            </Box>
            {/* Description */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
                About
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: selectedUser?.description && selectedUser.description !== 'No description' ? 'text.secondary' : 'text.disabled',
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                  fontStyle: selectedUser?.description && selectedUser.description !== 'No description' ? 'normal' : 'italic'
                }}
              >
                {selectedUser?.description && selectedUser.description !== 'No description' ? selectedUser.description : 'Not specified'}
              </Typography>
            </Box>

            {/* Professional Info - Compact Grid */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.primary' }}>
                Professional Information
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                {/* Field of Activity - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Field of Activity
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: selectedUser?.field_of_activity && selectedUser.field_of_activity !== 'Not specified' ? 'text.secondary' : 'text.disabled',
                      fontSize: '0.75rem',
                      wordBreak: 'break-word',
                      maxHeight: '60px',
                      overflow: 'auto',
                      fontStyle: selectedUser?.field_of_activity && selectedUser.field_of_activity !== 'Not specified' ? 'normal' : 'italic'
                    }}
                  >
                    {selectedUser?.field_of_activity && selectedUser.field_of_activity !== 'Not specified' ? selectedUser.field_of_activity : 'Not specified'}
                  </Typography>
                </Box>

                {/* Skills - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Skills
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: selectedUser?.skills && selectedUser.skills !== 'Not specified' ? 'text.secondary' : 'text.disabled',
                      fontSize: '0.75rem',
                      wordBreak: 'break-word',
                      maxHeight: '60px',
                      overflow: 'auto',
                      fontStyle: selectedUser?.skills && selectedUser.skills !== 'Not specified' ? 'normal' : 'italic'
                    }}
                  >
                    {selectedUser?.skills && selectedUser.skills !== 'Not specified' ? selectedUser.skills : 'Not specified'}
                  </Typography>
                </Box>

                {/* Interests & Drivers - Always show, span full width */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50',
                  gridColumn: '1 / -1' // Span full width for longer content
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Interests & Drivers
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: selectedUser?.hobbies_drivers && selectedUser.hobbies_drivers !== 'Not specified' ? 'text.secondary' : 'text.disabled',
                      fontSize: '0.75rem',
                      wordBreak: 'break-word',
                      maxHeight: '60px',
                      overflow: 'auto',
                      fontStyle: selectedUser?.hobbies_drivers && selectedUser.hobbies_drivers !== 'Not specified' ? 'normal' : 'italic'
                    }}
                  >
                    {selectedUser?.hobbies_drivers && selectedUser.hobbies_drivers !== 'Not specified' ? selectedUser.hobbies_drivers : 'Not specified'}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Contact Info - Compact */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
                Contact Information
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {/* LinkedIn - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    LinkedIn
                  </Typography>
                  {selectedUser?.linkedin && selectedUser.linkedin.trim() !== '' ? (
                    <Typography
                      variant="body2"
                      component="a"
                      href={selectedUser.linkedin.startsWith('http') ? selectedUser.linkedin : `https://${selectedUser.linkedin}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        color: 'primary.main',
                        textDecoration: 'none',
                        fontSize: '0.75rem',
                        wordBreak: 'break-all',
                        display: 'block',
                        '&:hover': { textDecoration: 'underline' }
                      }}
                    >
                      {selectedUser.linkedin}
                    </Typography>
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: 'text.disabled',
                        fontSize: '0.75rem',
                        fontStyle: 'italic'
                      }}
                    >
                      Not specified
                    </Typography>
                  )}
                </Box>

                {/* Birthday - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Birthday
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: selectedUser?.birthday && selectedUser.birthday !== 'Not specified' ? 'text.secondary' : 'text.disabled',
                      fontSize: '0.75rem',
                      fontStyle: selectedUser?.birthday && selectedUser.birthday !== 'Not specified' ? 'normal' : 'italic'
                    }}
                  >
                    {selectedUser?.birthday && selectedUser.birthday !== 'Not specified' ? selectedUser.birthday : 'Not specified'}
                  </Typography>
                </Box>

                {/* Telegram Link - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Telegram
                  </Typography>
                  {selectedUser?.telegram_link && selectedUser.telegram_link.trim() !== '' ? (
                    <Typography
                      variant="body2"
                      component="a"
                      href={`https://t.me/${selectedUser.telegram_link.replace('@', '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        color: 'primary.main',
                        textDecoration: 'none',
                        fontSize: '0.75rem',
                        wordBreak: 'break-all',
                        display: 'block',
                        '&:hover': { textDecoration: 'underline' }
                      }}
                    >
                      @{selectedUser.telegram_link.replace('@', '')}
                    </Typography>
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: 'text.disabled',
                        fontSize: '0.75rem',
                        fontStyle: 'italic'
                      }}
                    >
                      Not specified
                    </Typography>
                  )}
                </Box>

                {/* Groups - Always show */}
                <Box sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'grey.50'
                }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 0.5 }}>
                    Groups
                  </Typography>
                  {(() => {
                    const userGroups = selectedUser?.groups
                    if (!userGroups || !Array.isArray(userGroups) || userGroups.length === 0) {
                      return (
                        <Typography
                          variant="body2"
                          sx={{
                            color: 'text.disabled',
                            fontSize: '0.75rem',
                            fontStyle: 'italic'
                          }}
                        >
                          Not specified
                        </Typography>
                      )
                    }
                    // Filter to ensure all items are strings
                    const validGroups = userGroups.filter((g: any) => typeof g === 'string')
                    if (validGroups.length === 0) {
                      return (
                        <Typography
                          variant="body2"
                          sx={{
                            color: 'text.disabled',
                            fontSize: '0.75rem',
                            fontStyle: 'italic'
                          }}
                        >
                          Not specified
                        </Typography>
                      )
                    }
                    return (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {validGroups.map((group: string, index: number) => (
                          <Chip
                            key={index}
                            label={group}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.75rem' }}
                          />
                        ))}
                      </Box>
                    )
                  })()}
                </Box>
              </Box>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3, pt: 1 }}>
          <Button
            onClick={() => setDetailOpen(false)}
            variant="contained"
            sx={{ minWidth: 100 }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* User Form Dialog */}
      <UserForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSave={handleSaveUser}
        user={editingUser ? {
          user_id: editingUser.id,
          intro_name: editingUser.name,
          intro_location: editingUser.location,
          intro_description: editingUser.description,
          intro_linkedin: editingUser.linkedin,
          intro_hobbies_drivers: editingUser.hobbies_drivers,
          intro_skills: editingUser.skills,
          field_of_activity: editingUser.field_of_activity,
          intro_birthday: editingUser.birthday,
          intro_image: editingUser.image,
          user_telegram_link: editingUser.telegram_link || null,
          state: editingUser.status,
          notifications_enabled: editingUser.notifications_enabled !== undefined ? editingUser.notifications_enabled : true,
          matches_disabled: editingUser.matches_disabled !== undefined ? editingUser.matches_disabled : false,
          finishedonboarding: editingUser.finishedonboarding !== undefined ? (editingUser.finishedonboarding === true) : true
        } : null}
        mode={formMode}
        apiBase={base}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        disableRestoreFocus
        disableAutoFocus
        disableEnforceFocus
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="span">Delete User</Typography>
          <IconButton
            aria-label="close"
            onClick={() => setDeleteDialogOpen(false)}
            sx={{
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user "{userToDelete?.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Error and Success Notifications */}
      <Snackbar
        open={!!errorMessage}
        autoHideDuration={6000}
        onClose={() => setErrorMessage(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setErrorMessage(null)}
          severity="error"
          sx={{ width: '100%' }}
        >
          {errorMessage}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={4000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSuccessMessage(null)}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  )
}


