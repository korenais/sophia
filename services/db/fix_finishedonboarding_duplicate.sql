-- Fix duplicate finishedOnboarding columns
-- This script consolidates finishedonboarding and finishedOnboarding into a single column
-- WITHOUT losing any data

DO $$
BEGIN
    -- Check if both columns exist
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        
        RAISE NOTICE 'Both finishedonboarding columns exist. Merging data...';
        
        -- Update finishedOnboarding (camelCase) with values from finishedonboarding (lowercase)
        -- Use COALESCE to prefer non-null values, defaulting to camelCase if both are null
        UPDATE users 
        SET "finishedOnboarding" = COALESCE(
            CASE WHEN finishedonboarding IS NOT NULL THEN finishedonboarding ELSE NULL END,
            "finishedOnboarding"
        )
        WHERE finishedonboarding IS NOT NULL AND ("finishedOnboarding" IS NULL OR "finishedOnboarding" != finishedonboarding);
        
        RAISE NOTICE 'Data merged into finishedOnboarding column';
        
        -- Drop the lowercase column
        ALTER TABLE users DROP COLUMN IF EXISTS finishedonboarding;
        
        RAISE NOTICE 'Lowercase finishedonboarding column dropped';
        
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') THEN
        -- Only lowercase exists, rename it to camelCase
        RAISE NOTICE 'Only lowercase finishedonboarding exists. Renaming to finishedOnboarding...';
        
        ALTER TABLE users RENAME COLUMN finishedonboarding TO "finishedOnboarding";
        
        RAISE NOTICE 'Column renamed to finishedOnboarding';
        
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedOnboarding') THEN
        -- Only camelCase exists, that's fine
        RAISE NOTICE 'Only finishedOnboarding (camelCase) exists. No action needed.';
    ELSE
        -- Neither exists, create it
        RAISE NOTICE 'Neither column exists. Creating finishedOnboarding...';
        ALTER TABLE users ADD COLUMN "finishedOnboarding" boolean DEFAULT false;
    END IF;
    
    -- Ensure the column has the correct default
    ALTER TABLE users ALTER COLUMN "finishedOnboarding" SET DEFAULT false;
    
    -- Set default for any NULL values
    UPDATE users SET "finishedOnboarding" = false WHERE "finishedOnboarding" IS NULL;
    
    RAISE NOTICE 'finishedOnboarding column consolidation completed successfully';
END $$;

-- Verify only one column exists now
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('finishedonboarding', 'finishedOnboarding')) > 1 THEN
        RAISE WARNING 'Multiple finishedOnboarding columns still exist after consolidation';
    ELSE
        RAISE NOTICE 'Verified: Only one finishedOnboarding column exists';
    END IF;
END $$;
