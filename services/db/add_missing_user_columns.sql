-- Quick fix: Add missing notifications_enabled and matches_disabled columns
-- This script can be run immediately to fix the admin interface user list issue

-- Add notifications_enabled column if missing
ALTER TABLE IF EXISTS users 
ADD COLUMN IF NOT EXISTS notifications_enabled boolean DEFAULT true;

-- Add matches_disabled column if missing
ALTER TABLE IF EXISTS users 
ADD COLUMN IF NOT EXISTS matches_disabled boolean DEFAULT false;

-- Set default values for existing rows
UPDATE users SET notifications_enabled = true WHERE notifications_enabled IS NULL;
UPDATE users SET matches_disabled = false WHERE matches_disabled IS NULL;

-- Create index for notifications_enabled if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_users_notifications_enabled ON users(notifications_enabled);

-- Create notifications table if it doesn't exist (for notification system)
CREATE TABLE IF NOT EXISTS notifications (
  id bigserial primary key,
  message_text text not null,
  scheduled_at timestamptz,
  sent_at timestamptz,
  status text not null default 'scheduled', -- 'scheduled', 'sent', 'cancelled'
  recipient_type text not null default 'all', -- 'all', 'user', 'group'
  recipient_ids bigint[], -- array of user_ids for 'user' or 'group' types
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

-- Create match_blocks table if it doesn't exist (for match blocking functionality)
CREATE TABLE IF NOT EXISTS public.match_blocks (
    id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    blocked_user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, blocked_user_id)
);

CREATE INDEX IF NOT EXISTS idx_match_blocks_user ON public.match_blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_blocked ON public.match_blocks(blocked_user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_pair ON public.match_blocks(user_id, blocked_user_id);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Missing columns and tables have been added successfully!';
    RAISE NOTICE 'Admin interface should now be able to load the user list.';
END $$;
