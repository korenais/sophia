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
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
  Typography
} from '@mui/material'
import { Close } from '@mui/icons-material'
import * as React from 'react'
import { useEffect, useState } from 'react'

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

type UserFormProps = {
  open: boolean
  onClose: () => void
  onSave: (user: Partial<User>) => Promise<void>
  user?: User | null
  mode: 'create' | 'edit'
  apiBase?: string
}

export default function UserForm({ open, onClose, onSave, user, mode, apiBase }: UserFormProps) {
  const base = apiBase || window.location.origin
  const [formData, setFormData] = useState<Partial<User>>({
    user_id: 0,
    intro_name: '',
    intro_location: '',
    intro_description: '',
    intro_linkedin: '',
    intro_hobbies_drivers: '',
    intro_skills: '',
    field_of_activity: '',
    intro_birthday: '',
    intro_image: '',
    user_telegram_link: '',
    state: 'ACTIVE',
    notifications_enabled: true,
    matches_disabled: false,
    finishedonboarding: true
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [imageValidation, setImageValidation] = useState<{ valid: boolean, message: string } | null>(null)
  const [formInitialized, setFormInitialized] = useState(false)
  const [groups, setGroups] = useState<Array<{ id: number; name: string }>>([])
  const [userGroups, setUserGroups] = useState<number[]>([])
  const [newGroupName, setNewGroupName] = useState('')
  const [showNewGroupInput, setShowNewGroupInput] = useState(false)

  useEffect(() => {
    // Initialize form data when dialog opens or user data changes
    if (open) {
      if (mode === 'edit' && user) {
        setFormData({
          user_id: user.user_id,
          intro_name: user.intro_name || '',
          intro_location: user.intro_location || '',
          intro_description: user.intro_description || '',
          intro_linkedin: user.intro_linkedin || '',
          intro_hobbies_drivers: user.intro_hobbies_drivers || '',
          intro_skills: user.intro_skills || '',
          field_of_activity: user.field_of_activity || '',
          intro_birthday: user.intro_birthday || '',
          intro_image: user.intro_image || '',
          user_telegram_link: user.user_telegram_link || '',
          state: user.state || 'ACTIVE',
          notifications_enabled: user.notifications_enabled !== null ? user.notifications_enabled : true,
          matches_disabled: user.matches_disabled === true,  // Only true means disabled, null/false means enabled
          finishedonboarding: user.finishedonboarding !== null ? user.finishedonboarding : true
        })
        setFormInitialized(true)
      } else if (mode === 'create') {
        setFormData({
          user_id: 0,
          intro_name: '',
          intro_location: '',
          intro_description: '',
          intro_linkedin: '',
          intro_hobbies_drivers: '',
          intro_skills: '',
          field_of_activity: '',
          intro_birthday: '',
          intro_image: '',
          user_telegram_link: '',
          state: 'ACTIVE',
          notifications_enabled: true,
          matches_disabled: false,
          finishedonboarding: true
        })
        setFormInitialized(true)
      }
      setErrors({})
      // Fetch groups and user's groups when form opens
      if (mode === 'edit' && user) {
        fetchGroups()
        fetchUserGroups(user.user_id)
      } else {
        fetchGroups()
        setUserGroups([])
      }
    } else {
      // Reset when dialog closes
      setFormInitialized(false)
      setUserGroups([])
      setShowNewGroupInput(false)
      setNewGroupName('')
    }
  }, [open, mode, user]) // Update when user data changes

  const fetchGroups = async () => {
    try {
      const response = await fetch(`${base}/api/groups`)
      if (response.ok) {
        const groupsData = await response.json()
        setGroups(groupsData)
      }
    } catch (error) {
      console.error('Error fetching groups:', error)
    }
  }

  const fetchUserGroups = async (userId: number) => {
    try {
      const response = await fetch(`${base}/api/users/${userId}/groups`)
      if (response.ok) {
        const userGroupsData = await response.json()
        setUserGroups(userGroupsData.map((g: { id: number }) => g.id))
      }
    } catch (error) {
      console.error('Error fetching user groups:', error)
    }
  }

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) {
      setErrors({ ...errors, groups: 'Group name cannot be empty' })
      return
    }
    try {
      const response = await fetch(`${base}/api/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newGroupName.trim() })
      })
      if (response.ok) {
        const newGroup = await response.json()
        setGroups([...groups, newGroup])
        setNewGroupName('')
        setShowNewGroupInput(false) // Hide input field after successful creation
        setErrors({ ...errors, groups: '' })
        
        // If in edit mode, immediately save the group membership to API
        // handleGroupChange will update userGroups after successful API call
        if (mode === 'edit' && formData.user_id) {
          await handleGroupChange(newGroup.id, true)
        } else {
          // For create mode, just update local state
          setUserGroups(prev => {
            if (!prev.includes(newGroup.id)) {
              return [...prev, newGroup.id]
            }
            return prev
          })
        }
      } else {
        const error = await response.json()
        setErrors({ ...errors, groups: error.detail || 'Failed to create group' })
      }
    } catch (error) {
      setErrors({ ...errors, groups: 'Failed to create group' })
    }
  }

  const handleGroupChange = async (groupId: number, add: boolean) => {
    if (!formData.user_id || mode !== 'edit') {
      // For create mode, just update local state
      if (add) {
        setUserGroups([...userGroups, groupId])
      } else {
        setUserGroups(userGroups.filter(id => id !== groupId))
      }
      return
    }

    try {
      if (add) {
        const response = await fetch(`${base}/api/users/${formData.user_id}/groups`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group_ids: [groupId] })
        })
        if (response.ok) {
          // Update local state only after successful API call
          setUserGroups(prev => {
            if (!prev.includes(groupId)) {
              return [...prev, groupId]
            }
            return prev
          })
          // Clear any previous errors
          if (errors.groups) {
            setErrors(prev => {
              const newErrors = { ...prev }
              delete newErrors.groups
              return newErrors
            })
          }
        } else {
          const error = await response.json()
          setErrors({ ...errors, groups: error.detail || 'Failed to add group' })
          // Revert local state on error
          setUserGroups(prev => prev.filter(id => id !== groupId))
        }
      } else {
        const response = await fetch(`${base}/api/users/${formData.user_id}/groups/${groupId}`, {
          method: 'DELETE'
        })
        if (response.ok) {
          // Update local state only after successful API call
          setUserGroups(prev => prev.filter(id => id !== groupId))
          // Clear any previous errors
          if (errors.groups) {
            setErrors(prev => {
              const newErrors = { ...prev }
              delete newErrors.groups
              return newErrors
            })
          }
        } else {
          const error = await response.json()
          setErrors({ ...errors, groups: error.detail || 'Failed to remove group' })
          // Revert local state on error - add group back
          setUserGroups(prev => {
            if (!prev.includes(groupId)) {
              return [...prev, groupId]
            }
            return prev
          })
        }
      }
    } catch (error) {
      setErrors({ ...errors, groups: 'Failed to update groups' })
      // Revert local state on error
      if (add) {
        setUserGroups(prev => prev.filter(id => id !== groupId))
      } else {
        setUserGroups(prev => {
          if (!prev.includes(groupId)) {
            return [...prev, groupId]
          }
          return prev
        })
      }
    }
  }

  const handleChange = (field: keyof User) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }))
    }

    // Validate image when intro_image changes
    if (field === 'intro_image') {
      const validation = validateImage(value)
      setImageValidation(validation)
    }
  }

  const handleSelectChange = (field: keyof User) => (event: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }))
  }

  const handleTelegramValidation = async (event: React.FocusEvent<HTMLInputElement>) => {
    const telegramInput = event.target.value.trim()

    if (!telegramInput) {
      // Clear any existing errors if field is empty
      setErrors(prev => ({
        ...prev,
        user_telegram_link: ''
      }))
      return
    }

    // Check if input is a numeric user_id (Telegram user IDs are numeric strings)
    // If it's a valid numeric ID, skip API validation and accept it directly
    // User IDs are valid identifiers for users without usernames
    if (/^\d+$/.test(telegramInput)) {
      // It's a numeric user_id - accept it without API validation
      // This is valid for users who don't have a Telegram username
      setErrors(prev => ({
        ...prev,
        user_telegram_link: ''
      }))
      return
    }

    // Check if input looks like a name (contains spaces, Cyrillic, or other non-username characters)
    // If so, warn the user that they should enter username or user_id, not their display name
    if (/[\sА-Яа-яЁё]/.test(telegramInput) || telegramInput.length > 32) {
      setErrors(prev => ({
        ...prev,
        user_telegram_link: 'This looks like a display name. Please enter your Telegram username (e.g., @john_doe) or numeric User ID instead.'
      }))
      return
    }

    try {
      // Call API to validate Telegram username and get user info
      const response = await fetch(`${base}/api/validate-telegram-username`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: telegramInput }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to validate Telegram username')
      }

      const telegramData = await response.json()
      console.log('Telegram validation response:', telegramData)

      // Update the form data with the normalized username
      if (telegramData.normalized_username) {
        setFormData(prev => ({
          ...prev,
          user_telegram_link: telegramData.normalized_username
        }))
      }

      // Auto-populate user_id and chat_id if available (only for users who have interacted with bot)
      if (telegramData.user_id && mode === 'create') {
        setFormData(prev => ({
          ...prev,
          user_id: telegramData.user_id,
          // Note: chat_id is typically the same as user_id for private chats
          // We'll let the backend handle this
        }))
      }

      // Clear any existing errors
      setErrors(prev => ({
        ...prev,
        user_telegram_link: ''
      }))

    } catch (error) {
      console.error('Telegram validation error:', error)
      setErrors(prev => ({
        ...prev,
        user_telegram_link: error instanceof Error ? error.message : 'Invalid Telegram username'
      }))
    }
  }

  const handleLinkedInValidation = async (event: React.FocusEvent<HTMLInputElement>) => {
    const linkedinInput = event.target.value.trim()

    if (!linkedinInput) {
      setErrors(prev => ({
        ...prev,
        intro_linkedin: ''
      }))
      return
    }

    try {
      // Call API to validate LinkedIn URL and get profile data
      const response = await fetch(`${base}/api/validate-linkedin-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: linkedinInput }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to validate LinkedIn URL')
      }

      const linkedinData = await response.json()
      console.log('LinkedIn validation response:', linkedinData)

      // Update the form data with the validated URL
      if (linkedinData.is_valid) {
        setFormData(prev => ({
          ...prev,
          intro_linkedin: linkedinData.profile_data?.url || linkedinInput
        }))
      }

      // Note: LinkedIn profile data extraction is limited due to LinkedIn's anti-scraping measures
      // The validation and URL cleaning functionality is the main benefit

      // Clear any existing errors
      setErrors(prev => ({
        ...prev,
        intro_linkedin: ''
      }))

    } catch (error) {
      console.error('LinkedIn validation error:', error)
      setErrors(prev => ({
        ...prev,
        intro_linkedin: error instanceof Error ? error.message : 'Invalid LinkedIn URL'
      }))
    }
  }

  const validateImage = (imageData: string): { valid: boolean, message: string } => {
    if (!imageData || !imageData.trim()) {
      return { valid: true, message: 'No image provided' }
    }

    // Check if it's a data URL
    if (imageData.startsWith('data:image/')) {
      const parts = imageData.split(',')
      if (parts.length !== 2) {
        return { valid: false, message: 'Invalid data URL format' }
      }

      const mimeType = parts[0].split(':')[1]?.split(';')[0]
      if (!mimeType || !['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'].includes(mimeType)) {
        return { valid: false, message: 'Unsupported image format. Use JPEG, PNG, GIF, or WebP' }
      }

      const base64Data = parts[1]
      const sizeInBytes = (base64Data.length * 3) / 4
      const sizeInMB = sizeInBytes / (1024 * 1024)

      if (sizeInMB > 5) {
        return { valid: false, message: `Image too large (${sizeInMB.toFixed(1)}MB). Maximum size is 5MB` }
      }

      return { valid: true, message: `Valid ${mimeType} image (${sizeInMB.toFixed(1)}MB)` }
    }

    // Check if it's a URL
    if (imageData.startsWith('http://') || imageData.startsWith('https://')) {
      // Check if it's ui-avatars.com and suggest PNG format
      if (imageData.includes('ui-avatars.com') && !imageData.includes('format=')) {
        return { valid: true, message: 'Valid image URL (will be converted to PNG format for bot compatibility)' }
      }
      // Check if it's a placeholder service
      if (imageData.includes('dummyimage.com') || imageData.includes('picsum.photos')) {
        return { valid: true, message: 'Valid placeholder image URL' }
      }
      return { valid: true, message: 'Valid image URL' }
    }

    // Check if it's raw base64
    try {
      const decoded = atob(imageData)
      const sizeInBytes = decoded.length
      const sizeInMB = sizeInBytes / (1024 * 1024)

      if (sizeInMB > 5) {
        return { valid: false, message: `Image too large (${sizeInMB.toFixed(1)}MB). Maximum size is 5MB` }
      }

      return { valid: true, message: `Valid base64 image (${sizeInMB.toFixed(1)}MB)` }
    } catch {
      return { valid: false, message: 'Invalid image format. Use URL, data URL, or base64' }
    }
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setImageValidation({ valid: false, message: 'Please select an image file' })
      return
    }

    // Validate file size
    const sizeInMB = file.size / (1024 * 1024)
    if (sizeInMB > 5) {
      setImageValidation({ valid: false, message: `File too large (${sizeInMB.toFixed(1)}MB). Maximum size is 5MB` })
      return
    }

    // Convert to data URL
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      setFormData(prev => ({ ...prev, intro_image: dataUrl }))
      const validation = validateImage(dataUrl)
      setImageValidation(validation)
    }
    reader.readAsDataURL(file)
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.intro_name?.trim()) {
      newErrors.intro_name = 'Name is required'
    }

    if (mode === 'create' && !formData.user_telegram_link?.trim()) {
      newErrors.user_telegram_link = 'Telegram username or User ID is required'
    }

    // Validate user_telegram_link format: must be either valid username or numeric user_id
    if (formData.user_telegram_link?.trim()) {
      const telegramLink = formData.user_telegram_link.trim()
      // Check if it's a numeric user_id
      const isNumericId = /^\d+$/.test(telegramLink)
      // Check if it's a valid Telegram username (5-32 chars, alphanumeric + underscore)
      const isValidUsername = /^[a-zA-Z0-9_]{5,32}$/.test(telegramLink)

      if (!isNumericId && !isValidUsername) {
        newErrors.user_telegram_link = 'Must be a valid Telegram username (5-32 chars, alphanumeric + underscore) or numeric User ID'
      }
    }

    if (formData.intro_linkedin && !formData.intro_linkedin.includes('linkedin.com')) {
      newErrors.intro_linkedin = 'Please enter a valid LinkedIn URL'
    }

    // Allow empty birthday, but validate format if provided
    if (formData.intro_birthday && formData.intro_birthday.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(formData.intro_birthday)) {
      newErrors.intro_birthday = 'Please enter date in YYYY-MM-DD format or leave empty'
    }

    // Validate image if provided
    if (formData.intro_image && imageValidation && !imageValidation.valid) {
      newErrors.intro_image = imageValidation.message || 'Invalid image format'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {

    if (!validateForm()) {
      return
    }

    setLoading(true)
    try {
      // Convert form data to the expected format
      let processedImage = formData.intro_image?.trim() || null

      // If it's a ui-avatars.com URL without format parameter, add PNG format
      if (processedImage && processedImage.includes('ui-avatars.com') && !processedImage.includes('format=')) {
        processedImage = processedImage + '&format=png'
      }

      // If it's a data URL, extract the base64 part for storage
      if (processedImage && processedImage.startsWith('data:image/')) {
        const base64Data = processedImage.split(',')[1]
        processedImage = base64Data || null
      }

      // If it's an empty string, set to null to clear the field
      if (processedImage === '') {
        processedImage = null
      }

      const userData = {
        user_id: formData.user_id,
        intro_name: formData.intro_name,
        intro_location: formData.intro_location || null,
        intro_description: formData.intro_description || null,
        intro_linkedin: formData.intro_linkedin || null,
        intro_hobbies_drivers: formData.intro_hobbies_drivers || null,
        intro_skills: formData.intro_skills || null,
        field_of_activity: formData.field_of_activity || null,
        intro_birthday: formData.intro_birthday?.trim() || null,
        intro_image: processedImage,
        user_telegram_link: formData.user_telegram_link || null,
        state: formData.state,
        notifications_enabled: formData.notifications_enabled !== false,
        matches_disabled: formData.matches_disabled === true,
        finishedonboarding: Boolean(formData.finishedonboarding)
      }
      await onSave(userData)
      
      // Save groups if in edit mode
      if (mode === 'edit' && formData.user_id) {
        // Get current groups from API
        const currentGroupsResponse = await fetch(`${base}/api/users/${formData.user_id}/groups`)
        if (currentGroupsResponse.ok) {
          const currentGroups = await currentGroupsResponse.json()
          const currentGroupIds = currentGroups.map((g: { id: number }) => g.id)
          
          // Find groups to add and remove
          const toAdd = userGroups.filter(id => !currentGroupIds.includes(id))
          const toRemove = currentGroupIds.filter((id: number) => !userGroups.includes(id))
          
          // Add missing groups (safety check - should be empty if handleGroupChange worked correctly)
          if (toAdd.length > 0) {
            const addResponse = await fetch(`${base}/api/users/${formData.user_id}/groups`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ group_ids: toAdd })
            })
            if (!addResponse.ok) {
              console.error('Failed to add groups during save:', await addResponse.text().catch(() => 'Unknown error'))
            }
          }
          
          // Remove groups that should not be there (safety check)
          for (const groupId of toRemove) {
            const deleteResponse = await fetch(`${base}/api/users/${formData.user_id}/groups/${groupId}`, {
              method: 'DELETE'
            })
            if (!deleteResponse.ok) {
              console.error(`Failed to remove group ${groupId} during save:`, await deleteResponse.text().catch(() => 'Unknown error'))
            }
          }
        }
      }
      
      onClose()
    } catch (error) {
      console.error('Error saving user:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred'
      console.error('Error details:', errorMsg)
      setErrors({ submit: errorMsg })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({
      user_id: 0,
      intro_name: '',
      intro_location: '',
      intro_description: '',
      intro_linkedin: '',
      intro_hobbies_drivers: '',
      intro_skills: '',
      field_of_activity: '',
      intro_birthday: '',
      intro_image: '',
      user_telegram_link: '',
      state: 'ACTIVE',
      notifications_enabled: true,
      matches_disabled: false
    })
    setErrors({})
    setImageValidation(null)
    setFormInitialized(false) // Reset initialization flag
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      scroll="paper"
      disableRestoreFocus
      disableAutoFocus
      disableEnforceFocus
      TransitionProps={{ onExited: () => setImageValidation(null) }}
      PaperProps={{
        sx: {
          maxHeight: '95vh',
          height: 'auto',
          display: 'flex',
          flexDirection: 'column'
        }
      }}
    >
      <DialogTitle sx={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" component="span">
          {mode === 'create' ? 'Create New User' : 'Edit User'}
        </Typography>
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={{
            color: (theme) => theme.palette.grey[500],
          }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ overflow: 'auto', flex: '1 1 auto' }}>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Telegram Username"
                value={formData.user_telegram_link || ''}
                onChange={handleChange('user_telegram_link')}
                onBlur={handleTelegramValidation}
                error={!!errors.user_telegram_link}
                helperText={errors.user_telegram_link || "Accepts: @username, username, t.me/username, or numeric User ID (e.g., 123456789). Note: Do NOT enter your display name here - use Telegram username or User ID only."}
                placeholder="@john_doe, john_doe, t.me/john_doe, or 123456789"
                required
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Name"
                value={formData.intro_name || ''}
                onChange={handleChange('intro_name')}
                error={!!errors.intro_name}
                helperText={errors.intro_name}
                required
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Location"
                value={formData.intro_location || ''}
                onChange={handleChange('intro_location')}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="LinkedIn URL"
                value={formData.intro_linkedin || ''}
                onChange={handleChange('intro_linkedin')}
                onBlur={handleLinkedInValidation}
                error={!!errors.intro_linkedin}
                helperText={errors.intro_linkedin}
                placeholder="https://linkedin.com/in/username or leave empty"
              />
            </Grid>


            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Birthday (YYYY-MM-DD) - Optional"
                value={formData.intro_birthday || ''}
                onChange={handleChange('intro_birthday')}
                error={!!errors.intro_birthday}
                helperText={errors.intro_birthday || "Leave empty if you don't want to share your age"}
                placeholder="1990-05-15"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={formData.state || 'ACTIVE'}
                  onChange={handleSelectChange('state')}
                  label="Status"
                >
                  <MenuItem value="ACTIVE">Active</MenuItem>
                  <MenuItem value="INACTIVE">Inactive</MenuItem>
                  <MenuItem value="BANNED">Banned</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth error={!!errors.groups}>
                <InputLabel>Groups</InputLabel>
                {!showNewGroupInput ? (
                  <Select
                    multiple
                    value={userGroups}
                    onChange={(e) => {
                      const newValue = e.target.value as number[]
                      // Handle "Add new group" option (value -1)
                      if (newValue.includes(-1)) {
                        // Close the select dropdown by not including -1 in the value
                        setShowNewGroupInput(true)
                        setUserGroups(newValue.filter(v => v !== -1))
                      } else {
                        // Find which groups were added/removed
                        const added = newValue.filter(id => !userGroups.includes(id))
                        const removed = userGroups.filter(id => !newValue.includes(id))
                        
                        // Update groups one by one
                        added.forEach(id => handleGroupChange(id, true))
                        removed.forEach(id => handleGroupChange(id, false))
                      }
                    }}
                    label="Groups"
                    renderValue={(selected) => {
                      if (selected.length === 0) return 'No groups'
                      const selectedGroups = groups.filter(g => selected.includes(g.id))
                      return selectedGroups.map(g => g.name).join(', ')
                    }}
                  >
                    <MenuItem value={-1}>
                      <em>+ Add new group</em>
                    </MenuItem>
                    {groups.map((group) => (
                      <MenuItem key={group.id} value={group.id}>
                        {group.name}
                      </MenuItem>
                    ))}
                  </Select>
                ) : (
                  <Box sx={{ 
                    border: '1px solid rgba(0, 0, 0, 0.23)', 
                    borderRadius: '4px',
                    padding: '16.5px 14px',
                    minHeight: '56px',
                    display: 'flex',
                    alignItems: 'center',
                    backgroundColor: 'background.paper'
                  }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
                      Groups:
                    </Typography>
                    {userGroups.length > 0 ? (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, flex: 1 }}>
                        {userGroups.map((groupId) => {
                          const group = groups.find(g => g.id === groupId)
                          return group ? (
                            <Chip
                              key={groupId}
                              label={group.name}
                              size="small"
                              onDelete={() => handleGroupChange(groupId, false)}
                              sx={{ fontSize: '0.75rem' }}
                            />
                          ) : null
                        })}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                        No groups
                      </Typography>
                    )}
                  </Box>
                )}
                {showNewGroupInput && (
                  <Box sx={{ 
                    mt: 2, 
                    display: 'flex', 
                    gap: 1,
                    alignItems: 'flex-start',
                    zIndex: 1,
                    position: 'relative'
                  }}>
                    <TextField
                      fullWidth
                      size="small"
                      label="New group name"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleCreateGroup()
                        }
                      }}
                      autoFocus
                      sx={{ flex: 1 }}
                    />
                    <Button 
                      onClick={handleCreateGroup} 
                      variant="contained" 
                      size="small"
                      sx={{ mt: 0.5 }}
                    >
                      Create
                    </Button>
                    <Button 
                      onClick={() => { 
                        setShowNewGroupInput(false)
                        setNewGroupName('')
                      }} 
                      size="small"
                      sx={{ mt: 0.5 }}
                    >
                      Cancel
                    </Button>
                  </Box>
                )}
                {errors.groups && (
                  <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                    {errors.groups}
                  </Typography>
                )}
              </FormControl>
            </Grid>

            {/* Grouped Settings Section */}
            <Grid item xs={12}>
              <Box sx={{ 
                border: '1px solid rgba(0, 0, 0, 0.12)', 
                borderRadius: 1, 
                p: 2,
                backgroundColor: 'background.default'
              }}>
                <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: 'text.primary' }}>
                  Settings
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.notifications_enabled !== false}
                        onChange={(e) => setFormData(prev => ({ ...prev, notifications_enabled: e.target.checked }))}
                        color="success"
                      />
                    }
                    label="Notifications"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.matches_disabled !== true}
                        onChange={(e) => setFormData(prev => ({ ...prev, matches_disabled: !e.target.checked }))}
                        color="success"
                      />
                    }
                    label="Matches"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.finishedonboarding !== false}
                        onChange={(e) => setFormData(prev => ({ ...prev, finishedonboarding: e.target.checked }))}
                        color="success"
                      />
                    }
                    label="Registration Completed"
                  />
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                multiline
                rows={3}
                value={formData.intro_description || ''}
                onChange={handleChange('intro_description')}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Hobbies & Drivers"
                multiline
                rows={2}
                value={formData.intro_hobbies_drivers || ''}
                onChange={handleChange('intro_hobbies_drivers')}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Skills"
                multiline
                rows={2}
                value={formData.intro_skills || ''}
                onChange={handleChange('intro_skills')}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Field of Activity"
                multiline
                rows={2}
                value={formData.field_of_activity || ''}
                onChange={handleChange('field_of_activity')}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Avatar Image"
                multiline
                rows={3}
                value={formData.intro_image || ''}
                onChange={handleChange('intro_image')}
                helperText="Enter image URL, base64 data (data:image/jpeg;base64,...), or upload file"
                placeholder="https://example.com/avatar.jpg or data:image/jpeg;base64,/9j/4AAQ..."
              />
            </Grid>

            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
                <input
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="image-upload"
                  type="file"
                  onChange={handleFileUpload}
                />
                <label htmlFor="image-upload">
                  <Button variant="outlined" size="small" component="span">
                    Upload Image
                  </Button>
                </label>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setFormData(prev => ({ ...prev, intro_image: 'https://dummyimage.com/150x150/4CAF50/FFFFFF&text=' + encodeURIComponent(formData.intro_name || 'User') }))}
                >
                  Placeholder
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setFormData(prev => ({ ...prev, intro_image: 'https://picsum.photos/150/150' }))}
                >
                  Random Photo
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setFormData(prev => ({ ...prev, intro_image: 'https://ui-avatars.com/api/?name=' + encodeURIComponent(formData.intro_name || 'User') + '&background=4CAF50&color=FFFFFF&size=150&format=png' }))}
                >
                  Generate Avatar
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setFormData(prev => ({ ...prev, intro_image: '' }))}
                >
                  Clear Image
                </Button>
              </Box>

              {/* Image Validation Alert */}
              {imageValidation && (
                <Alert
                  severity={imageValidation.valid ? 'success' : 'error'}
                  sx={{ mb: 2 }}
                >
                  {imageValidation.message}
                </Alert>
              )}

              {/* Image Preview */}
              {formData.intro_image && imageValidation?.valid && (
                <Box sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Image Preview:
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <Avatar
                      src={formData.intro_image}
                      sx={{ width: 64, height: 64 }}
                      alt="Avatar preview"
                    />
                    <Typography variant="caption" sx={{ wordBreak: 'break-all' }}>
                      {formData.intro_image.length > 50
                        ? formData.intro_image.substring(0, 50) + '...'
                        : formData.intro_image}
                    </Typography>
                  </Box>
                  {/* Full-size preview */}
                  <Box sx={{ textAlign: 'center' }}>
                    <img
                      src={formData.intro_image}
                      alt="Full size preview"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '300px',
                        objectFit: 'contain',
                        border: '1px solid #ddd',
                        borderRadius: '4px'
                      }}
                    />
                  </Box>
                </Box>
              )}
            </Grid>
          </Grid>

          {errors.submit && (
            <Typography color="error" sx={{ mt: 2 }}>
              {errors.submit}
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ flexShrink: 0, borderTop: '1px solid rgba(0, 0, 0, 0.12)', pt: 1.5 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading}
        >
          {loading ? 'Saving...' : (mode === 'create' ? 'Create' : 'Save')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
