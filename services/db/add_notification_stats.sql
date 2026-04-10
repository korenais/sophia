-- Add statistics columns to notifications table for tracking sending results
ALTER TABLE IF EXISTS notifications 
ADD COLUMN IF NOT EXISTS sent_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS failed_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS error_message TEXT;

COMMENT ON COLUMN notifications.sent_count IS 'Number of users who successfully received the notification';
COMMENT ON COLUMN notifications.failed_count IS 'Number of users who failed to receive the notification';
COMMENT ON COLUMN notifications.error_message IS 'Error message if sending failed for all recipients or other critical error';
