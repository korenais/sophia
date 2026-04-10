-- Database schema verification script
-- This script verifies that all required tables and columns exist
-- Run this after deployment to ensure the database is properly set up

-- Check if all required tables exist
DO $$
DECLARE
    missing_tables TEXT[] := ARRAY[]::TEXT[];
    tbl_name TEXT;
    required_tables TEXT[] := ARRAY['users', 'meetings', 'feedbacks', 'thanks', 'bot_messages', 'user_groups', 'user_group_memberships', 'notifications', 'match_blocks'];
BEGIN
    FOREACH tbl_name IN ARRAY required_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = tbl_name
        ) THEN
            missing_tables := array_append(missing_tables, tbl_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Missing required tables: %', array_to_string(missing_tables, ', ');
    END IF;
    
    RAISE NOTICE 'All required tables exist';
END $$;

-- Check if all required columns exist in users table
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
    col_name TEXT;
    required_columns TEXT[] := ARRAY[
        'user_id', 'state', 'chat_id', 'language',
        'intro_name', 'intro_location', 'intro_description', 'intro_image', 
        'intro_linkedin', 'intro_hobbies_drivers', 'intro_skills', 'field_of_activity',
        'intro_birthday', 'vector_description', 'vector_location', 'finishedonboarding',
        'user_telegram_link', 'notifications_enabled', 'matches_disabled', 
        'last_birthday_greeting_sent', 'created_at', 'updated_at'
    ];
BEGIN
    FOREACH col_name IN ARRAY required_columns
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = col_name
        ) THEN
            missing_columns := array_append(missing_columns, col_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing required columns in users table: %', array_to_string(missing_columns, ', ');
    END IF;
    
    RAISE NOTICE 'All required columns exist in users table';
END $$;

-- Check if all required indexes exist
DO $$
DECLARE
    missing_indexes TEXT[] := ARRAY[]::TEXT[];
    index_name TEXT;
    required_indexes TEXT[] := ARRAY[
        'idx_users_finished_active', 'idx_users_telegram_link', 'idx_users_notifications_enabled',
        'idx_users_last_birthday_greeting',
        'idx_bot_messages_chat_created', 'idx_meetings_users', 
        'idx_meetings_status', 'idx_feedbacks_user',
        'idx_thanks_receiver', 'idx_thanks_sender',
        'idx_user_group_memberships_user_id', 'idx_user_group_memberships_group_id', 'idx_user_groups_name',
        'idx_notifications_status', 'idx_notifications_scheduled_at', 'idx_notifications_created_at',
        'idx_match_blocks_user', 'idx_match_blocks_blocked', 'idx_match_blocks_pair'
    ];
BEGIN
    FOREACH index_name IN ARRAY required_indexes
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE indexname = index_name
        ) THEN
            missing_indexes := array_append(missing_indexes, index_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_indexes, 1) > 0 THEN
        RAISE WARNING 'Missing indexes: %', array_to_string(missing_indexes, ', ');
    ELSE
        RAISE NOTICE 'All required indexes exist';
    END IF;
END $$;

-- Check new columns in users table
DO $$
BEGIN
    -- Check notifications_enabled
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') THEN
        RAISE EXCEPTION 'notifications_enabled column is missing - run migration script';
    END IF;
    
    -- Check matches_disabled
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') THEN
        RAISE EXCEPTION 'matches_disabled column is missing - run migration script';
    END IF;
    
    -- Check last_birthday_greeting_sent
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') THEN
        RAISE EXCEPTION 'last_birthday_greeting_sent column is missing - run migration script';
    END IF;
    
    -- Check field_of_activity
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'field_of_activity') THEN
        RAISE EXCEPTION 'field_of_activity column is missing - run migration script';
    END IF;
    
    RAISE NOTICE 'All new users table columns verified';
END $$;

-- Check notifications table and its new columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications') THEN
        RAISE EXCEPTION 'notifications table is missing - run migration script';
    END IF;
    
    -- Check image_url
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'image_url') THEN
        RAISE EXCEPTION 'notifications.image_url column is missing - run migration script';
    END IF;
    
    -- Check sent_count
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'sent_count') THEN
        RAISE EXCEPTION 'notifications.sent_count column is missing - run migration script';
    END IF;
    
    -- Check failed_count
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'failed_count') THEN
        RAISE EXCEPTION 'notifications.failed_count column is missing - run migration script';
    END IF;
    
    -- Check error_message
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notifications' AND column_name = 'error_message') THEN
        RAISE EXCEPTION 'notifications.error_message column is missing - run migration script';
    END IF;
    
    RAISE NOTICE 'All notifications table columns verified';
END $$;

-- Check match_blocks table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'match_blocks') THEN
        RAISE EXCEPTION 'match_blocks table is missing - run migration script';
    END IF;
    
    RAISE NOTICE 'match_blocks table verified';
END $$;

-- Final success message
DO $$
BEGIN
    RAISE NOTICE 'Database schema verification completed successfully';
    RAISE NOTICE 'All required tables, columns, and indexes are present';
END $$;
