-- Add image_url column to notifications table
-- This allows notifications to be sent as photos using bot.send_photo()
-- Telegram does not support <img> tags in HTML messages, so images must be sent separately

ALTER TABLE IF EXISTS notifications 
ADD COLUMN IF NOT EXISTS image_url TEXT;

COMMENT ON COLUMN notifications.image_url IS 'Optional image URL for photo notifications. When provided, notification is sent as photo with message_text as caption (max 1024 chars).';
