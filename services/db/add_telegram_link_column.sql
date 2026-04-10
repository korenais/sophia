-- Add user_telegram_link column to users table
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS user_telegram_link VARCHAR(255);

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_link ON public.users(user_telegram_link);

-- Update existing users with their Telegram usernames if available
-- This will be populated during onboarding process for new users
