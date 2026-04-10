-- Add column to track last birthday greeting sent date
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS last_birthday_greeting_sent date;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_users_last_birthday_greeting 
ON public.users(last_birthday_greeting_sent);
