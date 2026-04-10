import {
  Add,
  Block,
  Cancel,
  CheckCircle,
  Close,
  Delete,
  Edit,
  NotificationsOff,
  PersonOff,
  Schedule,
  Search,
  Send,
  Warning
} from '@mui/icons-material'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  IconButton,
  InputAdornment,
  Radio,
  RadioGroup,
  Snackbar,
  Stack,
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

type Notification = {
  id: number
  message_text: string
  scheduled_at: string | null
  sent_at: string | null
  status: 'scheduled' | 'sent' | 'cancelled'
  recipient_type: 'all' | 'user' | 'group' | 'user_group'
  recipient_ids: number[]
  image_url: string | null
  sent_count?: number
  failed_count?: number
  error_message?: string | null
  created_at: string
  updated_at: string
}

type UserGroup = {
  id: number
  name: string
  created_at: string
  updated_at: string
}

type GroupStatus = {
  group_id: number
  group_name: string
  status: 'OK' | 'NOT_OK'
  total_users: number
  problematic_users_count: number
  problematic_users: Array<{
    user_id: number
    intro_name: string | null
    issues: string[]
  }>
}

type User = {
  user_id: number
  intro_name: string | null
  notifications_enabled: boolean | null
  state: string | null
  user_telegram_link: string | null
  can_send_message?: boolean | null  // Whether bot can send message to this user (checked via Telegram API)
}

let handleEditNotification: (notification: Notification) => void
let handleDeleteNotification: (notification: Notification) => void
let handleSendNow: (notification: Notification) => void
let usersMap: Map<number, string> = new Map()
let groupsMap: Map<number, string> = new Map()

const getColumns = (users: User[], groups: UserGroup[]): GridColDef<Notification>[] => {
  // Update users map for quick lookup
  usersMap = new Map(users.map(u => [u.user_id, u.intro_name || `User ${u.user_id}`]))
  // Create local groups map for this render - this ensures renderCell always has current groups
  const localGroupsMap = new Map(groups.map(g => [g.id, g.name]))
  // Also update global for backward compatibility (if needed elsewhere)
  groupsMap = localGroupsMap

  return [
    {
      field: 'id',
      headerName: 'ID',
      width: 80
    },
    {
      field: 'message_text',
      headerName: 'Message',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => {
        const text = params.value || ''
        const preview = text.length > 100 ? text.substring(0, 100) + '...' : text
        // Strip HTML tags for preview
        const plainText = preview.replace(/<[^>]*>/g, '')
        return (
          <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
            {plainText}
          </Typography>
        )
      }
    },
    {
      field: 'recipient_type',
      headerName: 'Recipients',
      width: 200,
      flex: 1,
      minWidth: 150,
      renderCell: (params) => {
        const type = params.row.recipient_type
        const ids = params.row.recipient_ids || []

        if (type === 'all') {
          return (
            <Chip
              label="All users"
              size="small"
              color="primary"
              variant="outlined"
            />
          )
        }

        if (type === 'group') {
          return (
            <Chip
              label="Telegram Group"
              size="small"
              color="info"
              variant="outlined"
            />
          )
        }

        if (type === 'user_group') {
          // For user groups, show group names
          const foundGroupNames = ids
            .map(id => localGroupsMap.get(id))
            .filter(name => name !== undefined)
          
          // Separate found and deleted groups
          const foundGroups: Array<{ id: number; name: string }> = []
          const deletedGroups: number[] = []
          
          ids.forEach(id => {
            const name = localGroupsMap.get(id)
            if (name !== undefined) {
              foundGroups.push({ id, name })
            } else {
              deletedGroups.push(id)
            }
          })
          
          // Build display text
          let displayText = ''
          if (foundGroups.length > 0) {
            const displayNames = foundGroups.slice(0, 3).map(g => g.name)
            const remainingCount = Math.max(0, foundGroups.length - displayNames.length)
            displayText = displayNames.join(', ')
            if (remainingCount > 0) {
              displayText += ` +${remainingCount} more`
            }
          }
          
          // Add deleted groups info
          if (deletedGroups.length > 0) {
            const deletedText = deletedGroups.map(id => `Group ${id} (deleted)`).join(', ')
            if (displayText) {
              displayText += `, ${deletedText}`
            } else {
              displayText = deletedText
            }
          }
          
          // Build full list for tooltip
          const fullListParts: string[] = []
          foundGroups.forEach(g => fullListParts.push(g.name))
          deletedGroups.forEach(id => fullListParts.push(`Group ${id} (deleted)`))
          const fullList = fullListParts.join(', ')
          
          return (
            <Tooltip title={`User group: ${fullList}`} arrow placement="top">
              <Chip
                label={`User group: ${displayText || 'No groups'}`}
                size="small"
                color="secondary"
                variant="outlined"
                sx={{
                  maxWidth: '100%',
                  '& .MuiChip-label': {
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    display: 'block'
                  }
                }}
              />
            </Tooltip>
          )
        }

        // For specific users, show names
        const userNames = ids
          .map(id => usersMap.get(id))
          .filter(name => name !== undefined)
          .slice(0, 3) // Show first 3 names

        const remainingCount = Math.max(0, ids.length - userNames.length)

        let displayText = userNames.join(', ')
        if (remainingCount > 0) {
          displayText += ` +${remainingCount} more`
        }

        // If no names found, fallback to count
        if (userNames.length === 0) {
          displayText = `${ids.length} user(s)`
        }

        // Full list for tooltip
        const fullList = ids
          .map(id => usersMap.get(id) || `User ${id}`)
          .join(', ')

        return (
          <Tooltip title={fullList} arrow placement="top">
            <Chip
              label={displayText}
              size="small"
              color="secondary"
              variant="outlined"
              sx={{
                maxWidth: '100%',
                '& .MuiChip-label': {
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  display: 'block'
                }
              }}
            />
          </Tooltip>
        )
      }
    },
    {
      field: 'scheduled_at',
      headerName: 'Scheduled',
      width: 180,
      renderCell: (params) => {
        if (!params.value) return <Chip label="Send now" size="small" color="info" />
        const date = new Date(params.value)
        return (
          <Typography variant="body2">
            {date.toLocaleString()}
          </Typography>
        )
      }
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 180,
      renderCell: (params) => {
        const status = params.value
        const notification = params.row
        const color = status === 'sent' ? 'success' : status === 'cancelled' ? 'error' : 'warning'
        const icon = status === 'sent' ? <CheckCircle /> : status === 'cancelled' ? <Cancel /> : <Schedule />

        let label = status.charAt(0).toUpperCase() + status.slice(1)
        let tooltipText = ''

        // Show statistics for sent notifications
        if (status === 'sent' && notification.sent_count !== undefined && notification.failed_count !== undefined) {
          const sent = notification.sent_count || 0
          const failed = notification.failed_count || 0
          const total = sent + failed

          if (total > 0) {
            if (failed === 0) {
              tooltipText = `✅ Successfully sent to all ${sent} recipient(s)`
              label = `Sent (${sent})`
            } else if (sent === 0) {
              tooltipText = `❌ Failed to send to all ${failed} recipient(s)`
              if (notification.error_message) {
                tooltipText += `\n\nError details: ${notification.error_message}`
              }
              tooltipText += `\n\nPossible reasons: user blocked the bot, invalid chat ID, or network issues.`
              label = `Failed (${failed})`
            } else {
              tooltipText = `⚠️ Partially sent: ${sent} successful, ${failed} failed out of ${total} total recipients`
              if (notification.error_message) {
                tooltipText += `\n\nError details: ${notification.error_message}`
              }
              tooltipText += `\n\nFailed recipients may have blocked the bot or have invalid chat IDs.`
              label = `Partial (${sent}/${total})`
            }

            // Add recipient type context
            let recipientInfo = ''
            if (notification.recipient_type === 'all') {
              recipientInfo = 'All users'
            } else if (notification.recipient_type === 'user') {
              recipientInfo = `Specific users (${notification.recipient_ids?.length || 0} selected)`
            } else if (notification.recipient_type === 'user_group') {
              // Get group names from localGroupsMap (captured in closure)
              const recipientIds = notification.recipient_ids || []
              const groupInfoParts: string[] = []
              
              recipientIds.forEach(id => {
                const name = localGroupsMap.get(id)
                if (name !== undefined) {
                  groupInfoParts.push(name)
                } else {
                  groupInfoParts.push(`Group ${id} (deleted)`)
                }
              })
              
              if (groupInfoParts.length > 0) {
                recipientInfo = `User group: ${groupInfoParts.join(', ')}`
              } else {
                recipientInfo = 'User group(s)'
              }
            } else {
              // 'group' type - Telegram group
              recipientInfo = 'Telegram Group'
            }
            tooltipText = `Recipients: ${recipientInfo}\n\n${tooltipText}`
          }
        }

        // Determine display color based on statistics
        let displayColor: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' = color as any
        if (status === 'sent' && notification.failed_count !== undefined && notification.sent_count !== undefined) {
          const sent = notification.sent_count || 0
          const failed = notification.failed_count || 0
          if (failed > 0 && sent === 0) {
            displayColor = 'error'  // All failed
          } else if (failed > 0 && sent > 0) {
            displayColor = 'warning'  // Partial failure
          }
        }

        return (
          <Tooltip title={tooltipText || status} arrow>
            <Chip
              label={label}
              size="small"
              color={displayColor}
              icon={icon}
            />
          </Tooltip>
        )
      }
    },
    {
      field: 'sent_at',
      headerName: 'Sent At',
      width: 180,
      renderCell: (params) => {
        if (!params.value) return <Typography variant="body2" sx={{ color: 'text.secondary' }}>-</Typography>
        const date = new Date(params.value)
        return (
          <Typography variant="body2">
            {date.toLocaleString()}
          </Typography>
        )
      }
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 150,
      getActions: (params: GridRowParams<Notification>) => {
        const notification = params.row
        const actions = []

        if (notification.status === 'scheduled') {
          // Scheduled notifications (for future) can be edited, sent now, or cancelled
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => handleEditNotification(notification)}
            />,
            <GridActionsCellItem
              icon={<Send />}
              label="Send Now"
              onClick={() => handleSendNow(notification)}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => handleDeleteNotification(notification)}
            />
          )
        } else if (notification.status === 'sent') {
          // Sent notifications - check if it's "send now" (scheduled_at is null) or scheduled that was sent
          const isSendNow = notification.scheduled_at === null

          if (isSendNow) {
            // "Send now" messages can only be viewed, not edited
            actions.push(
              <GridActionsCellItem
                icon={<Edit />}
                label="View"
                onClick={() => handleEditNotification(notification)}
              />,
              <GridActionsCellItem
                icon={<Delete />}
                label="Delete"
                onClick={() => handleDeleteNotification(notification)}
              />
            )
          } else {
            // Scheduled messages that were sent can be viewed or deleted
            actions.push(
              <GridActionsCellItem
                icon={<Edit />}
                label="View"
                onClick={() => handleEditNotification(notification)}
              />,
              <GridActionsCellItem
                icon={<Delete />}
                label="Delete"
                onClick={() => handleDeleteNotification(notification)}
              />
            )
          }
        } else {
          // Cancelled notifications - can be viewed or deleted
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="View"
              onClick={() => handleEditNotification(notification)}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => handleDeleteNotification(notification)}
            />
          )
        }

        return actions
      }
    }
  ]
}

export const NotificationsTable: React.FC<{ apiBase?: string }> = ({ apiBase }) => {
  const base = apiBase || window.location.origin
  const [data, setData] = useState<Notification[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editingNotification, setEditingNotification] = useState<Notification | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [notificationToDelete, setNotificationToDelete] = useState<Notification | null>(null)
  const [selectedSentNotifications, setSelectedSentNotifications] = useState<number[]>([])
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form state
  const [messageText, setMessageText] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [scheduledAt, setScheduledAt] = useState<Date | null>(null)
  const [sendNow, setSendNow] = useState(true)
  const [recipientType, setRecipientType] = useState<'all' | 'user' | 'group' | 'user_group'>('all')
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([])
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([])
  const [groups, setGroups] = useState<UserGroup[]>([])
  const [groupStatuses, setGroupStatuses] = useState<Map<number, GroupStatus>>(new Map())
  const [htmlValidationErrors, setHtmlValidationErrors] = useState<string[]>([])
  const [telegramGroupName, setTelegramGroupName] = useState<string | null>(null)

  // Telegram HTML supported tags
  const TELEGRAM_SUPPORTED_TAGS = ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'a', 'code', 'pre', 'span', 'tg-spoiler']

  // Validate HTML for Telegram compatibility
  const validateTelegramHtml = (text: string): { isValid: boolean; errors: string[]; highlightedText: string } => {
    const errors: string[] = []
    let highlightedText = text

    if (!text.trim()) {
      return { isValid: true, errors: [], highlightedText }
    }

    // Find all HTML tags
    const tagRegex = /<\/?([a-zA-Z0-9!-]+)(?:\s[^>]*)?>/g
    const matches = Array.from(text.matchAll(tagRegex))

    const unsupportedTags = new Map<string, string[]>() // tag name -> array of full tag occurrences

    matches.forEach(match => {
      const fullTag = match[0]
      const tagName = match[1].toLowerCase()

      // Check for DOCTYPE and other document-level tags
      if (tagName.startsWith('!')) {
        if (!unsupportedTags.has(tagName)) {
          unsupportedTags.set(tagName, [])
        }
        unsupportedTags.get(tagName)!.push(fullTag)
        errors.push(`Unsupported document-level tag: ${fullTag}. Telegram does not support <!DOCTYPE>, <html>, <head>, <body>, <title>, <meta>, etc.`)
        return
      }

      // Check if tag is supported
      if (!TELEGRAM_SUPPORTED_TAGS.includes(tagName)) {
        if (!unsupportedTags.has(tagName)) {
          unsupportedTags.set(tagName, [])
        }
        unsupportedTags.get(tagName)!.push(fullTag)
        // Only add error once per tag type
        if (unsupportedTags.get(tagName)!.length === 1) {
          errors.push(`Unsupported tag: <${tagName}>. Telegram only supports: ${TELEGRAM_SUPPORTED_TAGS.join(', ')}. Please remove or replace <${tagName}> tags.`)
        }
      }

      // Special validation for <a> tag - must have href attribute
      if (tagName === 'a' && fullTag.includes('<a') && !fullTag.includes('href=')) {
        errors.push(`<a> tag must have href attribute. Found: ${fullTag}`)
      }
    })

    return {
      isValid: errors.length === 0,
      errors: errors.slice(0, 5), // Limit to 5 errors to avoid overwhelming the UI
      highlightedText
    }
  }

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${base}/api/notifications`)
      if (!response.ok) throw new Error('Failed to fetch notifications')
      const notifications = await response.json()
      setData(notifications)
    } catch (error) {
      console.error('Error fetching notifications:', error)
      setErrorMessage('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  const checkUserMessageAvailability = async (usersList: User[]) => {
    try {
      const userIds = usersList.map(u => u.user_id)
      if (userIds.length === 0) return


      const response = await fetch(`${base}/api/users/check-message-availability`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_ids: userIds })
      })

      if (response.ok) {
        const data = await response.json()
        const availabilityMap = new Map<number, boolean>()

        // Create a map of user_id -> can_send_message
        data.results.forEach((result: { user_id: number; can_send_message: boolean; error?: string }) => {
          availabilityMap.set(result.user_id, result.can_send_message)
        })

        // Update users with availability information
        // IMPORTANT: Only update can_send_message if we got a result from API
        // Don't overwrite with null/undefined if API didn't return a result for a user
        setUsers(prevUsers => {
          const updated = prevUsers.map(user => {
            // Only update if we have a result for this user from API
            if (availabilityMap.has(user.user_id)) {
              const canSend = availabilityMap.get(user.user_id) ?? null
              return {
                ...user,
                can_send_message: canSend
              }
            }
            // Keep existing can_send_message value if API didn't return a result
            return user
          })
          return updated
        })
      } else {
        console.error('[Message Availability] API error:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Error checking message availability:', error)
      // Don't fail silently - but don't block UI either
    }
  }

  const fetchUsers = async (checkAvailabilityIfUserType: boolean = false) => {
    try {
      const response = await fetch(`${base}/api/users`)
      if (!response.ok) throw new Error('Failed to fetch users')
      const usersData: User[] = await response.json()
      // Reset can_send_message when fetching fresh users (will be updated by checkUserMessageAvailability if called)
      const usersWithResetAvailability = usersData.map(u => ({ ...u, can_send_message: undefined }))
      setUsers(usersWithResetAvailability)

      // Check message availability if requested and recipient type is 'user'
      if (checkAvailabilityIfUserType && recipientType === 'user' && usersData.length > 0) {
        checkUserMessageAvailability(usersData)
      }
    } catch (error) {
      console.error('Error fetching users:', error)
    }
  }

  const fetchGroups = async () => {
    try {
      const response = await fetch(`${base}/api/groups`)
      if (response.ok) {
        const groupsData = await response.json()
        setGroups(groupsData)
        
        // Fetch status for each group
        const statusPromises = groupsData.map(async (group: UserGroup) => {
          try {
            const statusResponse = await fetch(`${base}/api/groups/${group.id}/status`)
            if (statusResponse.ok) {
              const status = await statusResponse.json()
              return { groupId: group.id, status }
            }
          } catch (error) {
            console.error(`Error fetching status for group ${group.id}:`, error)
          }
          return null
        })
        
        const statusResults = await Promise.all(statusPromises)
        const newStatuses = new Map<number, GroupStatus>()
        statusResults.forEach(result => {
          if (result) {
            newStatuses.set(result.groupId, result.status)
          }
        })
        setGroupStatuses(newStatuses)
      }
    } catch (error) {
      console.error('Error fetching groups:', error)
    }
  }

  const fetchTelegramGroupInfo = async () => {
    try {
      const response = await fetch(`${base}/api/telegram-group-info`)
      const data = await response.json()

      if (response.ok && data.group_name) {
        setTelegramGroupName(data.group_name)
      } else {
        // Log error message if available for debugging
        if (data.error) {
          console.warn('Telegram group info error:', data.error)
        } else {
          console.warn('Telegram group info API returned no group_name')
        }
        setTelegramGroupName(null)
      }
    } catch (error) {
      console.error('Error fetching Telegram group info:', error)
      setTelegramGroupName(null)
    }
  }

  useEffect(() => {
    fetchNotifications()
    fetchUsers()
    fetchTelegramGroupInfo()
    fetchGroups()
  }, [base])

  // Refresh users list, Telegram group info, and groups whenever the form dialog opens
  // This ensures user statuses (active/inactive/banned) and group name are always up-to-date
  useEffect(() => {
    if (formOpen) {
      // Check availability if recipient type is 'user'
      fetchUsers(true)
      fetchTelegramGroupInfo()
      fetchGroups()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formOpen])

  // Check message availability when recipient type changes to 'user'
  useEffect(() => {
    if (formOpen && recipientType === 'user' && users.length > 0) {
      // Check all users for message availability (API handles batching)
      checkUserMessageAvailability(users)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipientType])

  handleEditNotification = (notification: Notification) => {
    setEditingNotification(notification)
    setMessageText(notification.message_text)
    setImageUrl(notification.image_url || '')
    // For sent notifications, show sent_at; for others, show scheduled_at
    if (notification.status === 'sent' && notification.sent_at) {
      setScheduledAt(new Date(notification.sent_at))
      setSendNow(false) // Don't show "send now" for already sent notifications
    } else {
      setScheduledAt(notification.scheduled_at ? new Date(notification.scheduled_at) : null)
      setSendNow(!notification.scheduled_at)
    }
    setRecipientType(notification.recipient_type)
    if (notification.recipient_type === 'user_group') {
      setSelectedGroupIds(notification.recipient_ids || [])
      setSelectedUserIds([])
    } else if (notification.recipient_type === 'user') {
      setSelectedUserIds(notification.recipient_ids || [])
      setSelectedGroupIds([])
    } else {
      setSelectedUserIds([])
      setSelectedGroupIds([])
    }
    // Validate HTML when editing
    const validation = validateTelegramHtml(notification.message_text)
    setHtmlValidationErrors(validation.errors)
    setFormMode('edit')
    setFormOpen(true)
  }

  handleDeleteNotification = (notification: Notification) => {
    setNotificationToDelete(notification)
    setDeleteDialogOpen(true)
  }

  handleSendNow = async (notification: Notification) => {
    try {
      const response = await fetch(`${base}/api/notifications/${notification.id}/send`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to send notification')
      setSuccessMessage('Notification will be sent shortly')
      fetchNotifications()
    } catch (error) {
      console.error('Error sending notification:', error)
      setErrorMessage('Failed to send notification')
    }
  }

  const handleCreateNotification = () => {
    setEditingNotification(null)
    setMessageText('')
    setImageUrl('')
    setScheduledAt(null)
    setSendNow(true)
    setRecipientType('all')
    setSelectedUserIds([])
    setSelectedGroupIds([])
    setHtmlValidationErrors([])
    setFormMode('create')
    setFormOpen(true)
  }

  const handleSaveNotification = async () => {
    // Check if there are any available recipients before saving
    let hasAvailableRecipients = false
    let errorMsg = ''

    if (recipientType === 'all') {
      // Check if there are any users with notifications enabled and active state
      const enabledUsers = users.filter(u =>
        u.notifications_enabled !== false &&
        u.state === 'ACTIVE' &&
        u.intro_name
      )
      hasAvailableRecipients = enabledUsers.length > 0
      if (!hasAvailableRecipients) {
        errorMsg = 'Нет доступных пользователей (все отключили уведомления). Включите уведомления в профилях или выберите "User group".'
      }
    } else if (recipientType === 'user') {
      // Filter out users with notifications disabled
      const enabledUserIds = selectedUserIds.filter(userId => {
        const user = users.find(u => u.user_id === userId)
        return user &&
          user.notifications_enabled !== false &&
          user.state === 'ACTIVE' &&
          user.intro_name
      })

      if (enabledUserIds.length !== selectedUserIds.length) {
        setSelectedUserIds(enabledUserIds)
      }

      hasAvailableRecipients = enabledUserIds.length > 0
      if (!hasAvailableRecipients) {
        if (selectedUserIds.length > 0) {
          errorMsg = 'У выбранных пользователей отключены уведомления. Включите уведомления в профилях или выберите "User group".'
        } else {
          errorMsg = 'Выберите пользователей или "User group".'
        }
      }
    } else if (recipientType === 'group') {
      // Group notifications always have a recipient (the group)
      hasAvailableRecipients = true
    } else if (recipientType === 'user_group') {
      // Check if selected groups have any active users
      hasAvailableRecipients = selectedGroupIds.length > 0
      if (!hasAvailableRecipients) {
        errorMsg = 'Выберите группы пользователей.'
      }
    }

    if (!hasAvailableRecipients) {
      // Prevent saving if no recipients available
      setErrorMessage(errorMsg)
      return  // Always return - prevent saving
    }

    try {
      // Validate HTML before saving
      const validation = validateTelegramHtml(messageText)
      if (!validation.isValid) {
        setErrorMessage(`HTML validation failed: ${validation.errors[0]}${validation.errors.length > 1 ? ` (+${validation.errors.length - 1} more errors)` : ''}. Please fix the HTML before saving.`)
        return
      }

      // Validate caption length if image is provided (max 1024 chars for photo caption)
      if (imageUrl.trim() && messageText.replace(/<[^>]*>/g, '').length > 1024) {
        setErrorMessage('When using an image, caption text must be 1024 characters or less (HTML tags excluded)')
        return
      }

      // Validate scheduled date/time if "Send now" is not checked
      if (!sendNow && scheduledAt) {
        // Check if time is actually set (not just date)
        const scheduledDate = new Date(scheduledAt)
        const hours = scheduledDate.getHours()
        const minutes = scheduledDate.getMinutes()
        const seconds = scheduledDate.getSeconds()
        const milliseconds = scheduledDate.getMilliseconds()

        // If time components are all 0, it means only date was selected without time
        if (hours === 0 && minutes === 0 && seconds === 0 && milliseconds === 0) {
          setErrorMessage('Please specify a time for the scheduled notification. The time field cannot be empty.')
          return
        }
      }

      const notificationData = {
        message_text: messageText,
        image_url: imageUrl.trim() || null,
        scheduled_at: sendNow ? null : scheduledAt?.toISOString(),
        recipient_type: recipientType,
        recipient_ids: recipientType === 'all' || recipientType === 'group' 
          ? null 
          : recipientType === 'user_group' 
            ? selectedGroupIds 
            : selectedUserIds
      }

      let response
      if (formMode === 'create') {
        response = await fetch(`${base}/api/notifications`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(notificationData)
        })
      } else {
        response = await fetch(`${base}/api/notifications/${editingNotification!.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(notificationData)
        })
      }

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to save notification')
      }

      // If editing and "send now" is checked, trigger immediate sending
      if (formMode === 'edit' && sendNow) {
        try {
          const sendResponse = await fetch(`${base}/api/notifications/${editingNotification!.id}/send`, {
            method: 'POST'
          })
          if (!sendResponse.ok) {
            // Log but don't fail the update - notification was saved, just sending failed
            console.warn('Failed to trigger immediate send after update')
          } else {
            setSuccessMessage('Notification updated and will be sent immediately')
          }
        } catch (sendError) {
          console.error('Error triggering send after update:', sendError)
          // Still show success for update, just mention sending might be delayed
          setSuccessMessage('Notification updated successfully. Sending will be triggered shortly.')
        }
      } else {
        setSuccessMessage(`Notification ${formMode === 'create' ? 'created' : 'updated'} successfully`)
      }

      setFormOpen(false)
      fetchNotifications()
    } catch (error: any) {
      console.error('Error saving notification:', error)
      setErrorMessage(error.message || 'Failed to save notification')
    }
  }

  const handleDeleteConfirm = async () => {
    if (!notificationToDelete) return

    try {
      const response = await fetch(`${base}/api/notifications/${notificationToDelete.id}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete notification')
      setSuccessMessage('Notification deleted successfully')
      setDeleteDialogOpen(false)
      setNotificationToDelete(null)
      fetchNotifications()
    } catch (error) {
      console.error('Error deleting notification:', error)
      setErrorMessage('Failed to delete notification')
    }
  }

  const handleBulkDeleteConfirm = async () => {
    if (selectedSentNotifications.length === 0) return

    try {
      // Delete notifications one by one (can be parallelized if needed)
      const deletePromises = selectedSentNotifications.map(id =>
        fetch(`${base}/api/notifications/${id}`, { method: 'DELETE' })
      )
      const results = await Promise.allSettled(deletePromises)

      const failed = results.filter(r => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.ok))
      if (failed.length > 0) {
        throw new Error(`Failed to delete ${failed.length} notification(s)`)
      }

      setSuccessMessage(`Successfully deleted ${selectedSentNotifications.length} notification(s)`)
      setBulkDeleteDialogOpen(false)
      setSelectedSentNotifications([])
      fetchNotifications()
    } catch (error) {
      console.error('Error deleting notifications:', error)
      setErrorMessage(`Failed to delete notifications: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // Memoize columns to ensure they update when groups or users change
  const columns = useMemo(() => getColumns(users, groups), [users, groups])

  const filteredData = data.filter(notification => {
    const searchLower = searchTerm.toLowerCase()
    return (
      notification.message_text.toLowerCase().includes(searchLower) ||
      notification.status.toLowerCase().includes(searchLower) ||
      notification.recipient_type.toLowerCase().includes(searchLower)
    )
  })

  // Separate sent and non-sent notifications for selection
  const sentNotifications = filteredData.filter(n => n.status === 'sent')
  const sentNotificationIds = sentNotifications.map(n => n.id)

  // Handle row selection - only allow selection of sent messages
  const handleRowSelectionModelChange = (newSelection: readonly (string | number)[]) => {
    // Filter to only include sent notification IDs
    const validSelection = newSelection
      .filter((id): id is number => typeof id === 'number' && sentNotificationIds.includes(id))
    setSelectedSentNotifications(validSelection)
  }

  // Filter users that have a name (required for display)
  // IMPORTANT: Don't filter by can_send_message - show all users, even if they can't receive messages
  // This allows admins to see all users and their status
  const availableUsers = users.filter(u => u.intro_name)

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
            Status explanation: <strong>Sent (N)</strong> = successfully sent to N recipients;
            <strong> Failed (N)</strong> = failed for all N recipients;
            <strong> Partial (sent/failed)</strong> = sent to some, failed for others.
            Hover over status for details and error messages.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexGrow: 1, maxWidth: 600, ml: 2 }}>
          <TextField
            placeholder="Search notifications..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ flexGrow: 1 }}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
          {selectedSentNotifications.length > 0 && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<Delete />}
              onClick={() => setBulkDeleteDialogOpen(true)}
            >
              Delete Selected ({selectedSentNotifications.length})
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleCreateNotification}
          >
            Create Notification
          </Button>
        </Box>
      </Box>

      <Box sx={{ height: 500, width: '100%' }}>
        <DataGrid
          loading={loading}
          rows={filteredData}
          columns={columns}
          pageSizeOptions={[5, 10, 25]}
          pagination
          checkboxSelection
          disableRowSelectionOnClick
          rowSelectionModel={selectedSentNotifications}
          onRowSelectionModelChange={handleRowSelectionModelChange}
          isRowSelectable={(params) => params.row.status === 'sent'}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } }
          }}
          getRowId={(row) => row.id}
        />
      </Box>

      {/* Create/Edit Form Dialog */}
      <Dialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            maxHeight: '95vh',
            height: 'auto'
          }
        }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="span">
            {formMode === 'create'
              ? 'Create Notification'
              : editingNotification?.status === 'sent'
                ? 'View Notification (Sent)'
                : editingNotification?.status === 'cancelled'
                  ? 'View Notification (Cancelled)'
                  : 'Edit Notification'}
          </Typography>
          <IconButton
            aria-label="close"
            onClick={() => setFormOpen(false)}
            sx={{
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ overflow: 'visible' }}>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <FormLabel>Message Text (HTML supported)</FormLabel>
              <TextField
                multiline
                rows={10}
                value={messageText}
                onChange={(e) => {
                  const newValue = e.target.value
                  // Strip HTML tags for length calculation (Telegram counts actual characters)
                  const textWithoutTags = newValue.replace(/<[^>]*>/g, '')
                  // Telegram limit: 4096 characters for text messages, 1024 for photo captions
                  const maxLength = imageUrl.trim() ? 1024 : 4096
                  if (textWithoutTags.length <= maxLength) {
                    setMessageText(newValue)
                    // Validate HTML
                    const validation = validateTelegramHtml(newValue)
                    setHtmlValidationErrors(validation.errors)
                  }
                }}
                placeholder="Enter notification message. HTML tags are supported."
                fullWidth
                disabled={formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled')}
                error={
                  imageUrl.trim()
                    ? messageText.replace(/<[^>]*>/g, '').length > 1024 || htmlValidationErrors.length > 0
                    : messageText.replace(/<[^>]*>/g, '').length > 4096 || htmlValidationErrors.length > 0
                }
                helperText={(() => {
                  const textLength = messageText.replace(/<[^>]*>/g, '').length
                  const maxLength = imageUrl.trim() ? 1024 : 4096
                  const limitType = imageUrl.trim() ? 'photo caption' : 'text message'

                  if (formMode === 'edit' && editingNotification?.status === 'sent') {
                    return "This message has already been sent. It cannot be edited."
                  }

                  if (htmlValidationErrors.length > 0) {
                    return htmlValidationErrors[0] + (htmlValidationErrors.length > 1 ? ` (+${htmlValidationErrors.length - 1} more errors)` : '')
                  }

                  if (textLength > maxLength) {
                    return `Message too long: ${textLength}/${maxLength} characters (${limitType} limit)`
                  }
                  return `${textLength}/${maxLength} characters (${limitType} limit, HTML tags excluded). ${imageUrl.trim() ? 'Note: This will be sent as photo caption.' : 'Note: <img> tags are not supported by Telegram - use Image URL field instead.'}`
                })()}
                sx={{
                  '& .MuiInputBase-root': {
                    overflow: 'auto', // Enable scrolling
                    maxHeight: '400px', // Limit height
                  },
                  '& textarea': {
                    overflowY: 'auto !important',
                    overflowX: 'auto !important',
                  }
                }}
              />
            </FormControl>

            <TextField
              label="Image URL (optional)"
              value={imageUrl}
              onChange={(e) => {
                if (!(formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled'))) {
                  setImageUrl(e.target.value)
                }
              }}
              placeholder="https://example.com/image.jpg"
              fullWidth
              disabled={formMode === 'edit' && editingNotification?.status === 'sent'}
              helperText={
                imageUrl.trim()
                  ? "If image URL is provided, message text will be sent as photo caption (max 1024 characters). Note: Telegram does not support <img> tags in HTML messages."
                  : "Optional: Enter image URL to send notification as photo. Leave empty for text-only notification."
              }
            />

            {/* Hide "Send now" checkbox for sent notifications - they already show sent_at in the date field */}
            {!(formMode === 'edit' && editingNotification?.status === 'sent') && (
              <FormControl>
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={sendNow}
                        onChange={(e) => {
                          if (!(formMode === 'edit' && editingNotification?.status === 'cancelled')) {
                            setSendNow(e.target.checked)
                            if (e.target.checked) {
                              setScheduledAt(null)
                            }
                          }
                        }}
                        disabled={formMode === 'edit' && editingNotification?.status === 'cancelled'}
                      />
                    }
                    label="Send now"
                  />
                </FormGroup>
              </FormControl>
            )}

            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <TextField
                label={formMode === 'edit' && editingNotification?.status === 'sent' ? "Sent Date" : "Scheduled Date"}
                type="date"
                value={scheduledAt ? new Date(scheduledAt.getTime() - scheduledAt.getTimezoneOffset() * 60000).toISOString().slice(0, 10) : ''}
                onChange={(e) => {
                  if (!sendNow && !(formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled'))) {
                    const dateValue = e.target.value
                    if (dateValue) {
                      const currentTime = scheduledAt || new Date()
                      const [year, month, day] = dateValue.split('-').map(Number)
                      const newDate = new Date(currentTime)
                      newDate.setFullYear(year, month - 1, day)
                      setScheduledAt(newDate)
                    } else {
                      setScheduledAt(null)
                    }
                  }
                }}
                disabled={sendNow || (formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled'))}
                sx={{ flex: 1 }}
                helperText={
                  formMode === 'edit' && editingNotification?.status === 'sent'
                    ? "Date when notification was sent"
                    : sendNow
                      ? "Clear 'Send now' to schedule for a specific date and time"
                      : "Select date"
                }
                InputLabelProps={{
                  shrink: true,
                }}
              />
              <TextField
                label={formMode === 'edit' && editingNotification?.status === 'sent' ? "Sent Time" : "Scheduled Time"}
                type="time"
                value={scheduledAt ? new Date(scheduledAt.getTime() - scheduledAt.getTimezoneOffset() * 60000).toISOString().slice(11, 16) : ''}
                onChange={(e) => {
                  if (!sendNow && !(formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled'))) {
                    const timeValue = e.target.value
                    if (timeValue && scheduledAt) {
                      const [hours, minutes] = timeValue.split(':').map(Number)
                      const newDate = new Date(scheduledAt)
                      newDate.setHours(hours, minutes, 0, 0)
                      setScheduledAt(newDate)
                    } else if (timeValue) {
                      // If no date is set yet, use today's date
                      const [hours, minutes] = timeValue.split(':').map(Number)
                      const newDate = new Date()
                      newDate.setHours(hours, minutes, 0, 0)
                      setScheduledAt(newDate)
                    }
                  }
                }}
                disabled={sendNow || (formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled'))}
                sx={{ flex: 1 }}
                inputProps={{
                  step: 60, // 1 minute steps, no seconds
                }}
                helperText={
                  formMode === 'edit' && editingNotification?.status === 'sent'
                    ? "Time when notification was sent"
                    : "Enter time (HH:MM format, you can type directly)"
                }
                InputLabelProps={{
                  shrink: true,
                }}
              />
            </Box>

            <FormControl fullWidth>
              <FormLabel>Recipients</FormLabel>
              <Box sx={{ display: 'flex', flexDirection: 'row', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <RadioGroup
                  value={recipientType}
                  onChange={(e) => {
                    if (!(formMode === 'edit' && editingNotification?.status === 'sent')) {
                      const newType = e.target.value as 'all' | 'user' | 'group' | 'user_group'
                      setRecipientType(newType)
                      if (newType === 'all' || newType === 'group') {
                        setSelectedUserIds([])
                        setSelectedGroupIds([])
                      } else if (newType === 'user') {
                        setSelectedGroupIds([])
                      } else if (newType === 'user_group') {
                        setSelectedUserIds([])
                      }
                    }
                  }}
                  sx={{ minWidth: 200 }}
                >
                  <FormControlLabel
                    value="all"
                    control={<Radio disabled={formMode === 'edit' && editingNotification?.status === 'sent'} />}
                    label="All users"
                  />
                  <FormControlLabel
                    value="user"
                    control={<Radio disabled={formMode === 'edit' && editingNotification?.status === 'sent'} />}
                    label="Specific users"
                  />
                  <FormControlLabel
                    value="group"
                    control={<Radio disabled={formMode === 'edit' && editingNotification?.status === 'sent'} />}
                    label="Telegram group"
                  />
                  <FormControlLabel
                    value="user_group"
                    control={<Radio disabled={formMode === 'edit' && editingNotification?.status === 'sent'} />}
                    label="User group"
                  />
                </RadioGroup>

                {/* Show additional controls next to radio selection */}
                {recipientType === 'user' && (
                  <Box sx={{ flex: 1, minWidth: 300, maxWidth: 500 }}>
                    <Autocomplete
                      multiple
                      options={availableUsers}
                      getOptionLabel={(option) => {
                        const name = `${option.intro_name} (ID: ${option.user_id})`
                        if (option.notifications_enabled === false) {
                          return `${name} [Notifications disabled]`
                        }
                        if (option.can_send_message === false) {
                          return `${name} [Cannot send message]`
                        }
                        if (option.state === 'BANNED') {
                          return `${name} [Banned]`
                        }
                        if (option.state && option.state !== 'ACTIVE') {
                          return `${name} [${option.state}]`
                        }
                        return name
                      }}
                      getOptionDisabled={(option) => option.notifications_enabled === false}
                      value={availableUsers.filter(u => selectedUserIds.includes(u.user_id))}
                      onChange={(_, newValue) => {
                        if (!(formMode === 'edit' && editingNotification?.status === 'sent')) {
                          // Filter out users with notifications disabled as a safety measure
                          const enabledUsers = newValue.filter(u => u.notifications_enabled !== false)
                          setSelectedUserIds(enabledUsers.map(u => u.user_id))
                        }
                      }}
                      disabled={formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled')}
                      renderOption={(props, option) => {
                        const isDisabled = option.notifications_enabled === false
                        const isBanned = option.state === 'BANNED'
                        const isInactive = option.state && option.state !== 'ACTIVE' && !isBanned
                        // Check if can_send_message is explicitly false (not null/undefined)
                        const cannotSendMessage = option.can_send_message === false
                        // Check if user has no Telegram link (critical issue)
                        const hasNoTelegram = !option.user_telegram_link || option.user_telegram_link.trim() === ''
                        const showStatus = isDisabled || isBanned || isInactive || cannotSendMessage || hasNoTelegram

                        return (
                          <li {...props} style={{ ...props.style, opacity: showStatus ? 0.6 : 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                              {/* Status icons */}
                              {hasNoTelegram && <Block fontSize="small" color="error" />}
                              {isBanned && !hasNoTelegram && <Block fontSize="small" color="error" />}
                              {isInactive && !hasNoTelegram && !isBanned && <PersonOff fontSize="small" color="warning" />}
                              {cannotSendMessage && !isBanned && !isInactive && !hasNoTelegram && <Warning fontSize="small" color="warning" />}
                              {isDisabled && !isBanned && !isInactive && !cannotSendMessage && !hasNoTelegram && <NotificationsOff fontSize="small" color="disabled" />}

                              <span>{option.intro_name} (ID: {option.user_id})</span>

                              {/* Status chips */}
                              <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                                {hasNoTelegram && (
                                  <Tooltip title="No Telegram link - cannot send messages (critical)">
                                    <Chip
                                      icon={<Block />}
                                      label="❌ No Telegram"
                                      size="small"
                                      color="error"
                                      variant="outlined"
                                    />
                                  </Tooltip>
                                )}
                                {isBanned && !hasNoTelegram && (
                                  <Chip
                                    icon={<Block />}
                                    label="Banned"
                                    size="small"
                                    color="error"
                                    variant="outlined"
                                  />
                                )}
                                {isInactive && !hasNoTelegram && (
                                  <Chip
                                    icon={<PersonOff />}
                                    label={option.state || 'Inactive'}
                                    size="small"
                                    color="warning"
                                    variant="outlined"
                                  />
                                )}
                                {cannotSendMessage && !hasNoTelegram && (
                                  <Tooltip title="Bot cannot send message to this user (user hasn't started conversation with bot)">
                                    <Chip
                                      icon={<Warning />}
                                      label="Cannot send message"
                                      size="small"
                                      color="warning"
                                      variant="outlined"
                                    />
                                  </Tooltip>
                                )}
                                {isDisabled && !hasNoTelegram && (
                                  <Chip
                                    label="Notifications disabled"
                                    size="small"
                                    color="default"
                                    variant="outlined"
                                  />
                                )}
                              </Box>
                            </Box>
                          </li>
                        )
                      }}
                      renderInput={(params) => {
                        // Check if there are any users with disabled notifications or cannot send messages
                        const hasDisabledUsers = availableUsers.some(u => u.notifications_enabled === false)
                        const hasUnreachableUsers = availableUsers.some(u => u.can_send_message === false)

                        let helperText: string | undefined = undefined
                        if (hasDisabledUsers && hasUnreachableUsers) {
                          helperText = "Note: Users with notifications disabled or unreachable are displayed but may not be selectable"
                        } else if (hasDisabledUsers) {
                          helperText = "Note: Users with notifications disabled are displayed but cannot be selected"
                        } else if (hasUnreachableUsers) {
                          helperText = "Note: Some users may be unreachable (they haven't started conversation with bot)"
                        }

                        return (
                          <TextField
                            {...params}
                            label="Select users"
                            placeholder="Choose users"
                            helperText={helperText}
                          />
                        )
                      }}
                    />
                  </Box>
                )}

                {recipientType === 'group' && (
                  <Box sx={{ flex: 1, minWidth: 300, maxWidth: 500, pt: 1.5 }}>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      {telegramGroupName
                        ? `Notification will be sent to: ${telegramGroupName}`
                        : 'Notification will be sent to the configured Telegram group'}
                    </Typography>
                  </Box>
                )}

                {recipientType === 'user_group' && (
                  <Box sx={{ flex: 1, minWidth: 300, maxWidth: 500 }}>
                    <Autocomplete
                      multiple
                      options={groups}
                      getOptionLabel={(option) => {
                        const status = groupStatuses.get(option.id)
                        const statusIndicator = status?.status === 'OK' ? '✅' : status?.status === 'NOT_OK' ? '⚠️' : ''
                        return `${statusIndicator} ${option.name}`
                      }}
                      value={groups.filter(g => selectedGroupIds.includes(g.id))}
                      onChange={(_, newValue) => {
                        if (!(formMode === 'edit' && editingNotification?.status === 'sent')) {
                          setSelectedGroupIds(newValue.map(g => g.id))
                        }
                      }}
                      disabled={formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled')}
                      renderOption={(props, option) => {
                        const status = groupStatuses.get(option.id)
                        const isNotOk = status?.status === 'NOT_OK'
                        const problematicCount = status?.problematic_users_count || 0
                        const problematicUsers = status?.problematic_users || []
                        
                        // Format issues for tooltip
                        const formatIssues = (user: { intro_name: string | null; issues: string[] }) => {
                          const issueLabels: Record<string, string> = {
                            'no_telegram_link': '❌ No Telegram (critical)',
                            'negative_user_id': '❌ Negative ID - group, not private chat (critical)',
                            'notifications_disabled': '❌ Notifications disabled (will be filtered)',
                            'state_inactive': 'Inactive',
                            'state_banned': 'Banned',
                            'not_finished_onboarding': 'Registration incomplete',
                            'cannot_receive_messages': 'Cannot receive messages (bot blocked or no conversation started)'
                          }
                          const labels = user.issues.map(issue => issueLabels[issue] || issue).join(', ')
                          return `${user.intro_name || `User`}: ${labels}`
                        }
                        
                        return (
                          <li {...props} style={{ ...props.style, opacity: isNotOk ? 0.8 : 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                              {isNotOk && <Warning fontSize="small" color="warning" />}
                              {!isNotOk && <CheckCircle fontSize="small" color="success" />}
                              <span>{option.name}</span>
                              {isNotOk && (
                                <Tooltip
                                  title={
                                    problematicCount > 0
                                      ? `Issues with ${problematicCount} user(s):\n${problematicUsers.map(formatIssues).join('\n')}${problematicCount > 3 ? '\n...' : ''}`
                                      : 'Some users may have issues receiving notifications'
                                  }
                                  arrow
                                >
                                  <Chip
                                    label={`${problematicCount} issue(s)`}
                                    size="small"
                                    color="warning"
                                    variant="outlined"
                                    sx={{ ml: 'auto' }}
                                  />
                                </Tooltip>
                              )}
                            </Box>
                          </li>
                        )
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Select groups"
                          placeholder="Choose groups"
                          helperText="Select one or more user groups. Users in multiple selected groups will receive the message only once."
                        />
                      )}
                    />
                  </Box>
                )}
              </Box>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)}>Close</Button>
          {!(formMode === 'edit' && (editingNotification?.status === 'sent' || editingNotification?.status === 'cancelled')) && (
            <Button
              onClick={handleSaveNotification}
              variant="contained"
              disabled={
                !messageText.trim() ||
                (recipientType === 'user' && selectedUserIds.length === 0) ||
                (recipientType === 'user_group' && selectedGroupIds.length === 0) ||
                htmlValidationErrors.length > 0 ||
                (imageUrl.trim()
                  ? messageText.replace(/<[^>]*>/g, '').length > 1024  // Photo caption limit
                  : messageText.replace(/<[^>]*>/g, '').length > 4096) // Text message limit
              }
            >
              {formMode === 'create' ? 'Create' : 'Update'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="span">Delete Notification</Typography>
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
            Are you sure you want to {notificationToDelete?.status === 'sent' ? 'delete' : 'cancel'} this notification?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>No, Keep It</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            {notificationToDelete?.status === 'sent' ? 'Yes, Delete' : 'Yes, Cancel Notification'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog open={bulkDeleteDialogOpen} onClose={() => setBulkDeleteDialogOpen(false)}>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="span">Delete Selected Notifications</Typography>
          <IconButton
            aria-label="close"
            onClick={() => setBulkDeleteDialogOpen(false)}
            sx={{
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {selectedSentNotifications.length} sent notification(s)? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleBulkDeleteConfirm} color="error" variant="contained">
            Delete {selectedSentNotifications.length}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!errorMessage}
        autoHideDuration={6000}
        onClose={() => setErrorMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setErrorMessage(null)} severity="error">
          {errorMessage}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setSuccessMessage(null)} severity="success">
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  )
}
