-- Production Migration Script
-- This script safely adds all new fields and tables to production database
-- It checks for existence before adding to avoid errors on re-runs
-- Run this script on production server to update database schema

-- ============================================
-- 1. Add new columns to users table
-- ============================================

DO $$
BEGIN
    -- Add notifications_enabled column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') THEN
        ALTER TABLE users ADD COLUMN notifications_enabled boolean DEFAULT true;
        RAISE NOTICE 'Added notifications_enabled column to users table';
    ELSE
        RAISE NOTICE 'notifications_enabled column already exists';
    END IF;
    
    -- Add matches_disabled column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') THEN
        ALTER TABLE users ADD COLUMN matches_disabled boolean DEFAULT false;
        RAISE NOTICE 'Added matches_disabled column to users table';
    ELSE
        RAISE NOTICE 'matches_disabled column already exists';
    END IF;
    
    -- Add last_birthday_greeting_sent column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') THEN
        ALTER TABLE users ADD COLUMN last_birthday_greeting_sent date;
        RAISE NOTICE 'Added last_birthday_greeting_sent column to users table';
    ELSE
        RAISE NOTICE 'last_birthday_greeting_sent column already exists';
    END IF;
    
    -- Set default values for existing rows
    UPDATE users SET notifications_enabled = true WHERE notifications_enabled IS NULL;
    UPDATE users SET matches_disabled = false WHERE matches_disabled IS NULL;
    
    RAISE NOTICE 'Users table migration completed';
END $$;

-- Create indexes for new columns if they don't exist
CREATE INDEX IF NOT EXISTS idx_users_notifications_enabled ON users(notifications_enabled);
CREATE INDEX IF NOT EXISTS idx_users_last_birthday_greeting ON users(last_birthday_greeting_sent);

-- ============================================
-- 2. Create notifications table if it doesn't exist
-- ============================================

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

-- ============================================
-- 3. Add new columns to notifications table
-- ============================================

DO $$
BEGIN
    -- Add image_url column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'image_url') THEN
        ALTER TABLE notifications ADD COLUMN image_url text;
        RAISE NOTICE 'Added image_url column to notifications table';
    ELSE
        RAISE NOTICE 'image_url column already exists';
    END IF;
    
    -- Add sent_count column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'sent_count') THEN
        ALTER TABLE notifications ADD COLUMN sent_count integer DEFAULT 0;
        RAISE NOTICE 'Added sent_count column to notifications table';
    ELSE
        RAISE NOTICE 'sent_count column already exists';
    END IF;
    
    -- Add failed_count column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'failed_count') THEN
        ALTER TABLE notifications ADD COLUMN failed_count integer DEFAULT 0;
        RAISE NOTICE 'Added failed_count column to notifications table';
    ELSE
        RAISE NOTICE 'failed_count column already exists';
    END IF;
    
    -- Add error_message column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'error_message') THEN
        ALTER TABLE notifications ADD COLUMN error_message text;
        RAISE NOTICE 'Added error_message column to notifications table';
    ELSE
        RAISE NOTICE 'error_message column already exists';
    END IF;
    
    -- Set default values for existing rows
    UPDATE notifications SET sent_count = 0 WHERE sent_count IS NULL;
    UPDATE notifications SET failed_count = 0 WHERE failed_count IS NULL;
    
    RAISE NOTICE 'Notifications table migration completed';
END $$;

-- Create indexes for notifications table if they don't exist
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================
-- 4. Create user_groups tables if they don't exist
-- ============================================

CREATE TABLE IF NOT EXISTS user_groups (
  id bigserial primary key,
  name text not null unique,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

CREATE TABLE IF NOT EXISTS user_group_memberships (
  user_id bigint not null references users(user_id) on delete cascade,
  group_id bigint not null references user_groups(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, group_id)
);

-- Create indexes for user_groups tables if they don't exist
CREATE INDEX IF NOT EXISTS idx_user_group_memberships_user_id ON user_group_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_user_group_memberships_group_id ON user_group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_user_groups_name ON user_groups(name);

-- ============================================
-- 5. Create match_blocks table if it doesn't exist
-- ============================================

CREATE TABLE IF NOT EXISTS public.match_blocks (
    id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    blocked_user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, blocked_user_id)
);

-- Create indexes for match_blocks table if they don't exist
CREATE INDEX IF NOT EXISTS idx_match_blocks_user ON public.match_blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_blocked ON public.match_blocks(blocked_user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_pair ON public.match_blocks(user_id, blocked_user_id);

-- ============================================
-- 6. Verification
-- ============================================

DO $$
DECLARE
    missing_items TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Check users table columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') THEN
        missing_items := array_append(missing_items, 'users.notifications_enabled');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') THEN
        missing_items := array_append(missing_items, 'users.matches_disabled');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') THEN
        missing_items := array_append(missing_items, 'users.last_birthday_greeting_sent');
    END IF;
    
    -- Check notifications table
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications') THEN
        missing_items := array_append(missing_items, 'notifications table');
    END IF;
    
    -- Check notifications table columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'image_url') THEN
        missing_items := array_append(missing_items, 'notifications.image_url');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'sent_count') THEN
        missing_items := array_append(missing_items, 'notifications.sent_count');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'failed_count') THEN
        missing_items := array_append(missing_items, 'notifications.failed_count');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'error_message') THEN
        missing_items := array_append(missing_items, 'notifications.error_message');
    END IF;
    
    -- Check user_groups tables
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_groups') THEN
        missing_items := array_append(missing_items, 'user_groups table');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_group_memberships') THEN
        missing_items := array_append(missing_items, 'user_group_memberships table');
    END IF;
    
    -- Check match_blocks table
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'match_blocks') THEN
        missing_items := array_append(missing_items, 'match_blocks table');
    END IF;
    
    IF array_length(missing_items, 1) > 0 THEN
        RAISE WARNING 'Some items are still missing: %', array_to_string(missing_items, ', ');
    ELSE
        RAISE NOTICE '✅ All new fields and tables have been successfully added!';
        RAISE NOTICE 'Migration completed successfully';
    END IF;
END $$;

