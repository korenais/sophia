-- Verification script to check finishedOnboarding migration status
-- Run this after migration to verify everything is correct

DO $$
DECLARE
    has_lowercase BOOLEAN;
    has_camelcase BOOLEAN;
    total_users INTEGER;
    users_with_lowercase INTEGER;
    users_with_camelcase INTEGER;
BEGIN
    -- Check which columns exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedonboarding'
    ) INTO has_lowercase;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
    ) INTO has_camelcase;
    
    -- Count users
    SELECT COUNT(*) INTO total_users FROM users;
    
    IF has_lowercase THEN
        SELECT COUNT(*) INTO users_with_lowercase FROM users WHERE finishedonboarding IS NOT NULL;
    END IF;
    
    IF has_camelcase THEN
        SELECT COUNT(*) INTO users_with_camelcase FROM users WHERE "finishedOnboarding" IS NOT NULL;
    END IF;
    
    -- Report status
    RAISE NOTICE '========================================';
    RAISE NOTICE 'finishedOnboarding Migration Status';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total users: %', total_users;
    RAISE NOTICE 'finishedonboarding (lowercase) column exists: %', has_lowercase;
    RAISE NOTICE 'finishedOnboarding (camelCase) column exists: %', has_camelcase;
    
    IF has_lowercase THEN
        RAISE NOTICE 'Users with finishedonboarding data: %', users_with_lowercase;
    END IF;
    
    IF has_camelcase THEN
        RAISE NOTICE 'Users with finishedOnboarding data: %', users_with_camelcase;
    END IF;
    
    RAISE NOTICE '----------------------------------------';
    
    -- Verify migration completed correctly
    IF has_camelcase THEN
        RAISE WARNING 'MIGRATION INCOMPLETE: finishedOnboarding (camelCase) column still exists!';
        RAISE WARNING 'Please run migrate_to_finishedonboarding_lowercase.sql';
    ELSIF NOT has_lowercase THEN
        RAISE WARNING 'MIGRATION ERROR: finishedonboarding (lowercase) column does not exist!';
    ELSE
        RAISE NOTICE 'SUCCESS: Only finishedonboarding (lowercase) column exists';
        RAISE NOTICE 'Migration completed successfully!';
    END IF;
    
    RAISE NOTICE '========================================';
END $$;

-- Show sample of data
SELECT 
    user_id,
    intro_name,
    finishedonboarding,
    state
FROM users 
ORDER BY updated_at DESC 
LIMIT 10;
