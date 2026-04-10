# Features Available in Admin Interface

## Notifications Table (NotificationsTable component)

All requested features are implemented:

✅ **Message Text Field**
- Multiline text input
- HTML support (can paste formatted text with images)
- Placeholder: "Enter notification message. HTML tags are supported. You can paste formatted text with images."

✅ **Send Now Checkbox**
- Checkbox labeled "Send now"
- When checked, disables date/time picker
- Sets `scheduled_at` to NULL

✅ **Date & Time Picker**
- Type: `datetime-local` input
- Visible when "Send now" is unchecked
- Allows selecting date and time for scheduled delivery

✅ **Recipient Selection**
- Radio buttons for:
  - "All users" (default)
  - "Specific users"
  - "User group"
- When "Specific users" or "User group" selected, shows Autocomplete component
- Autocomplete allows selecting multiple users by name

✅ **Actions**
- Create button ("Create Notification")
- Edit button (for scheduled notifications)
- Send Now button (for scheduled notifications)
- Delete/Cancel button
- View button (for sent notifications, read-only)

✅ **Notification List**
- Shows all notifications in DataGrid
- Columns: ID, Message (preview), Recipients, Scheduled At, Sent At, Status, Actions
- Search functionality
- Pagination

## User Profile (PeopleTable / UserForm)

✅ **Disable Notifications Toggle**
- Switch component in user edit form
- Label: "Enable Notifications"
- Updates `notifications_enabled` field in database

✅ **Visual Indicator**
- Chip with `NotificationsOff` icon
- Shown in PeopleTable when user has notifications disabled
- Tooltip: "Notifications disabled"

## Location in Admin Panel

The NotificationsTable component is rendered in `main.tsx` at line 43, after:
- PeopleTable
- MatchesTable
- FeedbackTable
- ThanksTable

## Browser Cache

If you don't see the updated interface:
1. Hard refresh the browser (Ctrl+Shift+R or Ctrl+F5)
2. Clear browser cache
3. Check browser console for errors
