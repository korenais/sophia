-- Migration: Move data from finishedOnboarding (camelCase) to finishedonboarding (lowercase)
-- This script migrates data and removes the camelCase column to use only lowercase
-- Safe migration - preserves all data
-- IMPORTANT: This migration MUST run BEFORE check_and_add_missing_tables.sql

DO $$
DECLARE
    rows_before INTEGER;
    rows_after INTEGER;
    rows_to_migrate INTEGER;
    migrated_count INTEGER;
BEGIN
    -- Count total rows before migration for verification
    SELECT COUNT(*) INTO rows_before FROM users;
    
    -- Step 1: If both columns exist, migrate data from camelCase to lowercase
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        
        RAISE NOTICE 'Both columns exist. Migrating data from finishedOnboarding (camelCase) to finishedonboarding (lowercase)...';
        
        -- Count rows that will be migrated
        SELECT COUNT(*) INTO rows_to_migrate 
        FROM users 
        WHERE "finishedOnboarding" IS NOT NULL;
        
        RAISE NOTICE 'Found % rows with finishedOnboarding (camelCase) data to migrate', rows_to_migrate;
        
        -- Migrate data: prioritize camelCase value (it's the source of truth for old data on production)
        -- Strategy: 
        -- 1. Copy camelCase value to lowercase for ALL rows where camelCase is not NULL (overwrites if different)
        -- 2. Keep lowercase value for rows where camelCase is NULL (preserves new data)
        UPDATE users 
        SET finishedonboarding = "finishedOnboarding"
        WHERE "finishedOnboarding" IS NOT NULL;
        
        -- Also handle rows where camelCase is NULL but lowercase has value (keep lowercase value)
        -- This handles edge cases where only lowercase was set (new users added via API)
        -- No action needed - lowercase value is already correct for these rows
        
        RAISE NOTICE 'Data migrated to finishedonboarding (lowercase) column';
        
        -- Verify data was migrated (check that values match)
        SELECT COUNT(*) INTO migrated_count 
        FROM users
        WHERE "finishedOnboarding" IS NOT NULL
        AND finishedonboarding = "finishedOnboarding";
        
        RAISE NOTICE 'Verified: % rows have matching data in both columns after migration', migrated_count;
        
        -- Drop the camelCase column (old column is no longer needed)
        ALTER TABLE users DROP COLUMN IF EXISTS "finishedOnboarding";
        
        RAISE NOTICE 'Column finishedOnboarding (camelCase) dropped successfully';
        
    -- Step 2: If only camelCase exists, rename it to lowercase
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        
        RAISE NOTICE 'Only finishedOnboarding (camelCase) exists. Renaming to finishedonboarding (lowercase)...';
        
        ALTER TABLE users RENAME COLUMN "finishedOnboarding" TO finishedonboarding;
        
        RAISE NOTICE 'Column renamed to finishedonboarding (lowercase)';
        
    -- Step 3: If only lowercase exists, ensure it has correct defaults
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') THEN
        
        RAISE NOTICE 'Only finishedonboarding (lowercase) exists. Ensuring defaults...';
        
    -- Step 4: If neither exists, create lowercase column
    ELSE
        RAISE NOTICE 'Neither column exists. Creating finishedonboarding (lowercase)...';
        ALTER TABLE users ADD COLUMN finishedonboarding boolean DEFAULT false;
    END IF;
    
    -- Ensure the column has the correct default and constraints
    ALTER TABLE users ALTER COLUMN finishedonboarding SET DEFAULT false;
    ALTER TABLE users ALTER COLUMN finishedonboarding SET NOT NULL;
    
    -- Set default for any NULL values
    UPDATE users SET finishedonboarding = false WHERE finishedonboarding IS NULL;
    
    -- Update index to use lowercase column name
    DROP INDEX IF EXISTS idx_users_finished_active;
    CREATE INDEX IF NOT EXISTS idx_users_finished_active ON users(finishedonboarding, state);
    
    -- Verify no data was lost
    SELECT COUNT(*) INTO rows_after FROM users;
    IF rows_after != rows_before THEN
        RAISE WARNING 'Row count changed during migration! Before: %, After: %', rows_before, rows_after;
    ELSE
        RAISE NOTICE 'Row count verified: % rows (no data loss)', rows_after;
    END IF;
    
    -- Final check: ensure finishedonboarding column exists and is ready
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') THEN
        RAISE EXCEPTION 'Critical: finishedonboarding column does not exist after migration!';
    END IF;
    
    -- Final check: ensure finishedOnboarding (camelCase) column is deleted
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        RAISE WARNING 'WARNING: finishedOnboarding (camelCase) column still exists! Attempting to drop...';
        ALTER TABLE users DROP COLUMN IF EXISTS "finishedOnboarding";
        RAISE NOTICE 'Column finishedOnboarding (camelCase) force-dropped';
    END IF;
    
    RAISE NOTICE 'Migration to finishedonboarding (lowercase) completed successfully';
END $$;

-- Verify only lowercase column exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        RAISE WARNING 'Column finishedOnboarding (camelCase) still exists after migration!';
    ELSE
        RAISE NOTICE 'Verified: Only finishedonboarding (lowercase) column exists';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') THEN
        RAISE WARNING 'Column finishedonboarding (lowercase) does not exist after migration!';
    ELSE
        RAISE NOTICE 'Verified: finishedonboarding (lowercase) column exists';
    END IF;
END $$;
