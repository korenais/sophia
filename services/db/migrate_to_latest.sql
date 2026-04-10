-- Comprehensive migration script to ensure all tables and columns are up to date
-- This script can be run safely on existing databases

-- Add user_telegram_link column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_telegram_link VARCHAR(255);

-- Add index for user_telegram_link if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_users_telegram_link ON users(user_telegram_link);

-- Ensure language column exists with proper default
ALTER TABLE users ADD COLUMN IF NOT EXISTS language text DEFAULT 'en';

-- Set default value for existing rows if language is NULL
UPDATE users SET language = 'en' WHERE language IS NULL;

-- Set default value for the column
ALTER TABLE users ALTER COLUMN language SET DEFAULT 'en';

-- Ensure sent_followup_message column exists in meetings table
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS sent_followup_message boolean DEFAULT false;

-- Update any existing records to have the default value
UPDATE meetings SET sent_followup_message = false WHERE sent_followup_message IS NULL;

-- Add field_of_activity column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS field_of_activity TEXT;

-- Update existing records to have a default value if they don't have one
UPDATE users SET field_of_activity = 'Not specified' WHERE field_of_activity IS NULL;

-- Add comment to the column
COMMENT ON COLUMN users.field_of_activity IS 'Field of activity/profession of the user';

-- Verify field_of_activity column was added successfully
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'field_of_activity'
    ) THEN
        RAISE EXCEPTION 'field_of_activity column was not created successfully';
    END IF;
    
    RAISE NOTICE 'field_of_activity column verified successfully';
END $$;

-- Ensure all necessary indexes exist
CREATE INDEX IF NOT EXISTS idx_users_finished_active ON users(finishedonboarding, state);
CREATE INDEX IF NOT EXISTS idx_bot_messages_chat_created ON bot_messages(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_meetings_users ON meetings(user_1_id, user_2_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_feedbacks_user ON feedbacks(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_thanks_receiver ON thanks(receiver_username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_thanks_sender ON thanks(sender_user_id, created_at DESC);

-- Verify all tables exist
DO $$
BEGIN
    -- Check if all required tables exist
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        RAISE EXCEPTION 'users table does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'meetings') THEN
        RAISE EXCEPTION 'meetings table does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'feedbacks') THEN
        RAISE EXCEPTION 'feedbacks table does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'thanks') THEN
        RAISE EXCEPTION 'thanks table does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bot_messages') THEN
        RAISE EXCEPTION 'bot_messages table does not exist';
    END IF;
    
    RAISE NOTICE 'All required tables exist and migration completed successfully';
END $$;
