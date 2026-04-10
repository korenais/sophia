-- Check and Add Missing Tables and Columns
-- This script safely adds missing tables and columns to existing database
-- WITHOUT dropping any existing data

-- Check and create bot_messages table if it doesn't exist
CREATE TABLE IF NOT EXISTS bot_messages (
  id bigserial primary key,
  user_id bigint,
  chat_id bigint not null,
  text text,
  created_at timestamp with time zone default now()
);

-- Create index if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_bot_messages_chat_created ON bot_messages(chat_id, created_at DESC);

-- Check and add missing columns to users table
DO $$
BEGIN
    -- Add state column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'state') THEN
        ALTER TABLE users ADD COLUMN state text DEFAULT 'ACTIVE';
    END IF;
    
    -- Add chat_id column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'chat_id') THEN
        ALTER TABLE users ADD COLUMN chat_id bigint;
    END IF;
    
    -- Add language column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'language') THEN
        ALTER TABLE users ADD COLUMN language text DEFAULT 'en';
    END IF;
    
    -- Add username column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'username') THEN
        ALTER TABLE users ADD COLUMN username text;
    END IF;
    
    -- Add username_updated_at column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'username_updated_at') THEN
        ALTER TABLE users ADD COLUMN username_updated_at timestamptz;
    END IF;
    
    -- Add intro_name column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_name') THEN
        ALTER TABLE users ADD COLUMN intro_name text;
    END IF;
    
    -- Add intro_location column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_location') THEN
        ALTER TABLE users ADD COLUMN intro_location text;
    END IF;
    
    -- Add intro_description column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_description') THEN
        ALTER TABLE users ADD COLUMN intro_description text;
    END IF;
    
    -- Add intro_image column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_image') THEN
        ALTER TABLE users ADD COLUMN intro_image text;
    END IF;
    
    -- Add intro_linkedin column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_linkedin') THEN
        ALTER TABLE users ADD COLUMN intro_linkedin text;
    END IF;
    
    -- Add intro_hobbies_drivers column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_hobbies_drivers') THEN
        ALTER TABLE users ADD COLUMN intro_hobbies_drivers text;
    END IF;
    
    -- Add intro_skills column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_skills') THEN
        ALTER TABLE users ADD COLUMN intro_skills text;
    END IF;
    
    -- Add intro_birthday column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'intro_birthday') THEN
        ALTER TABLE users ADD COLUMN intro_birthday date;
    END IF;
    
    -- Add field_of_activity column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'field_of_activity') THEN
        ALTER TABLE users ADD COLUMN field_of_activity text;
    END IF;
    
    -- Add vector_description column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'vector_description') THEN
        ALTER TABLE users ADD COLUMN vector_description double precision[];
    END IF;
    
    -- Add vector_location column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'vector_location') THEN
        ALTER TABLE users ADD COLUMN vector_location text;
    END IF;
    
    -- Add finishedonboarding column if missing (lowercase only)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') THEN
        ALTER TABLE users ADD COLUMN finishedonboarding boolean DEFAULT false;
    END IF;
    
    -- Add user_telegram_link column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'user_telegram_link') THEN
        ALTER TABLE users ADD COLUMN user_telegram_link varchar(255);
    END IF;
    
    -- Add created_at column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'created_at') THEN
        ALTER TABLE users ADD COLUMN created_at timestamptz DEFAULT now();
    END IF;
    
    -- Add updated_at column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'updated_at') THEN
        ALTER TABLE users ADD COLUMN updated_at timestamptz DEFAULT now();
    END IF;
    
    -- Add notifications_enabled column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') THEN
        ALTER TABLE users ADD COLUMN notifications_enabled boolean DEFAULT true;
    END IF;
    
    -- Add matches_disabled column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') THEN
        ALTER TABLE users ADD COLUMN matches_disabled boolean DEFAULT false;
    END IF;
    
    -- Set default values for existing rows where needed
    UPDATE users SET state = 'ACTIVE' WHERE state IS NULL;
    UPDATE users SET language = 'en' WHERE language IS NULL;
    UPDATE users SET finishedonboarding = false WHERE finishedonboarding IS NULL;
    UPDATE users SET notifications_enabled = true WHERE notifications_enabled IS NULL;
    UPDATE users SET matches_disabled = false WHERE matches_disabled IS NULL;
    
    -- Add last_birthday_greeting_sent column if missing (for birthday greeting tracking)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') THEN
        ALTER TABLE users ADD COLUMN last_birthday_greeting_sent date;
        RAISE NOTICE 'Added last_birthday_greeting_sent column to users table';
    END IF;
    
    -- Add matches_disabled column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') THEN
        ALTER TABLE users ADD COLUMN matches_disabled boolean DEFAULT false;
        RAISE NOTICE 'Added matches_disabled column to users table';
    END IF;
    
    -- Set default values for new columns on existing rows
    UPDATE users SET matches_disabled = false WHERE matches_disabled IS NULL;
    
    RAISE NOTICE 'Users table columns checked and missing ones added';
END $$;

-- Create indexes for users table if they don't exist
CREATE INDEX IF NOT EXISTS idx_users_finished_active ON users(finishedonboarding, state);
CREATE INDEX IF NOT EXISTS idx_users_telegram_link ON users(user_telegram_link);
CREATE INDEX IF NOT EXISTS idx_users_notifications_enabled ON users(notifications_enabled);
CREATE INDEX IF NOT EXISTS idx_users_last_birthday_greeting ON users(last_birthday_greeting_sent);

-- Check and create meetings table if it doesn't exist
CREATE TABLE IF NOT EXISTS meetings (
  id bigserial primary key,
  user_1_id bigint not null references users(user_id) on delete cascade,
  user_2_id bigint not null references users(user_id) on delete cascade,
  status text not null default 'new',
  call_successful boolean,
  sent_followup_message boolean default false,
  created_at timestamptz default now(),
  last_updated timestamptz default now()
);

-- Add missing columns to meetings table if it already existed
DO $$
BEGIN
    -- Add sent_followup_message column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meetings' AND column_name = 'sent_followup_message') THEN
        ALTER TABLE meetings ADD COLUMN sent_followup_message boolean DEFAULT false;
    END IF;
    
    -- Add last_updated column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meetings' AND column_name = 'last_updated') THEN
        ALTER TABLE meetings ADD COLUMN last_updated timestamptz DEFAULT now();
    END IF;
    
    -- Set default values for existing rows
    UPDATE meetings SET sent_followup_message = false WHERE sent_followup_message IS NULL;
    
    RAISE NOTICE 'Meetings table columns checked and missing ones added';
END $$;

-- Create indexes for meetings table if they don't exist
CREATE INDEX IF NOT EXISTS idx_meetings_users ON meetings(user_1_id, user_2_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);

-- Check and create feedbacks table if it doesn't exist
CREATE TABLE IF NOT EXISTS feedbacks (
  id bigserial primary key,
  user_id bigint not null,
  type text not null,
  text text not null,
  created_at timestamptz default now()
);

-- Create index for feedbacks table if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_feedbacks_user ON feedbacks(user_id, created_at DESC);

-- Check and create thanks table if it doesn't exist
CREATE TABLE IF NOT EXISTS thanks (
  id bigserial primary key,
  sender_user_id bigint not null,
  receiver_username text not null,
  sender_username text not null,
  created_at timestamptz default now()
);

-- Create indexes for thanks table if they don't exist
CREATE INDEX IF NOT EXISTS idx_thanks_receiver ON thanks(receiver_username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_thanks_sender ON thanks(sender_user_id, created_at DESC);

-- Check and create notifications table if it doesn't exist
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

-- Add image_url column if missing (for photo notifications)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'image_url') THEN
        ALTER TABLE notifications ADD COLUMN image_url text;
        RAISE NOTICE 'Added image_url column to notifications table';
    END IF;
    
    -- Add sent_count column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'sent_count') THEN
        ALTER TABLE notifications ADD COLUMN sent_count integer DEFAULT 0;
        RAISE NOTICE 'Added sent_count column to notifications table';
    END IF;
    
    -- Add failed_count column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'failed_count') THEN
        ALTER TABLE notifications ADD COLUMN failed_count integer DEFAULT 0;
        RAISE NOTICE 'Added failed_count column to notifications table';
    END IF;
    
    -- Add error_message column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'error_message') THEN
        ALTER TABLE notifications ADD COLUMN error_message text;
        RAISE NOTICE 'Added error_message column to notifications table';
    END IF;
    
    -- Set default values for existing rows
    UPDATE notifications SET sent_count = 0 WHERE sent_count IS NULL;
    UPDATE notifications SET failed_count = 0 WHERE failed_count IS NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

-- Check and create user_groups tables if they don't exist
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

-- Check and create match_blocks table if it doesn't exist
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

-- Final verification message
DO $$
BEGIN
    RAISE NOTICE 'Database schema check completed. All missing tables and columns have been added safely.';
    RAISE NOTICE 'Existing data has been preserved.';
END $$;
