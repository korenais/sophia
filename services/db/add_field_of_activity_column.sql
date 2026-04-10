-- Migration script to add field_of_activity column to users table
-- This script can be run safely on existing databases
-- Version: 1.0
-- Date: 2024-10-18

-- Check if the column already exists
DO $$
BEGIN
    -- Add field_of_activity column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'field_of_activity'
    ) THEN
        -- Add the column
        ALTER TABLE users ADD COLUMN field_of_activity TEXT;
        
        -- Update existing records to have a default value
        UPDATE users SET field_of_activity = 'Not specified' WHERE field_of_activity IS NULL;
        
        -- Add comment to the column
        COMMENT ON COLUMN users.field_of_activity IS 'Field of activity/profession of the user';
        
        RAISE NOTICE 'field_of_activity column added successfully';
    ELSE
        RAISE NOTICE 'field_of_activity column already exists, skipping creation';
    END IF;
END $$;

-- Verify the column was created successfully
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'field_of_activity'
    ) THEN
        RAISE EXCEPTION 'field_of_activity column was not created successfully';
    END IF;
    
    -- Check if any users have NULL values and fix them
    IF EXISTS (SELECT 1 FROM users WHERE field_of_activity IS NULL) THEN
        UPDATE users SET field_of_activity = 'Not specified' WHERE field_of_activity IS NULL;
        RAISE NOTICE 'Updated NULL field_of_activity values to default';
    END IF;
    
    RAISE NOTICE 'field_of_activity column migration completed successfully';
END $$;