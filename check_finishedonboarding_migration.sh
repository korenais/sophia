#!/bin/bash
# Diagnostic script to check finishedonboarding migration status and data integrity
# Usage: ./check_finishedonboarding_migration.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "finishedonboarding Migration Diagnostic"
echo "=========================================="
echo ""

# Get container name from docker-compose
DB_CONTAINER="infra_db_1"

# Check if container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}ERROR: Database container '$DB_CONTAINER' is not running${NC}"
    exit 1
fi

echo -e "${GREEN}âœ“ Database container is running${NC}"
echo ""

echo "=== Step 1: Check which columns exist ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'users' 
AND (column_name = 'finishedonboarding' OR column_name = 'finishedOnboarding')
ORDER BY column_name;
"
echo ""

echo "=== Step 2: Count total users ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT COUNT(*) as total_users FROM users;
"
echo ""

echo "=== Step 3: Check finishedonboarding (lowercase) column status ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    finishedonboarding,
    COUNT(*) as user_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM users
GROUP BY finishedonboarding
ORDER BY finishedonboarding NULLS LAST;
"
echo ""

echo "=== Step 4: Check if finishedOnboarding (camelCase) still exists ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
        ) THEN 'EXISTS - MIGRATION INCOMPLETE!'
        ELSE 'DOES NOT EXIST - OK'
    END as camelcase_column_status;
"
echo ""

echo "=== Step 5: Compare data if both columns exist ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
DO \$\$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
    ) THEN
        RAISE NOTICE 'Both columns exist - comparing data...';
    ELSE
        RAISE NOTICE 'Only lowercase column exists (migration completed)';
    END IF;
END \$\$;
"

if docker exec "$DB_CONTAINER" psql -U postgres -d postgres -t -c "
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
    );
" | grep -q "t"; then
    echo ""
    echo "=== Comparing data between columns (if both exist) ==="
    echo ""
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        CASE 
            WHEN finishedonboarding = \"finishedOnboarding\" THEN 'MATCH'
            WHEN finishedonboarding IS NULL AND \"finishedOnboarding\" IS NULL THEN 'BOTH NULL'
            WHEN finishedonboarding IS NULL AND \"finishedOnboarding\" IS NOT NULL THEN 'LOWERCASE NULL, CAMELCASE HAS VALUE'
            WHEN finishedonboarding IS NOT NULL AND \"finishedOnboarding\" IS NULL THEN 'LOWERCASE HAS VALUE, CAMELCASE NULL'
            WHEN finishedonboarding != \"finishedOnboarding\" THEN 'MISMATCH'
            ELSE 'UNKNOWN'
        END as comparison_status,
        COUNT(*) as user_count
    FROM users
    GROUP BY comparison_status
    ORDER BY user_count DESC;
    "
    echo ""
    
    echo "=== Users with mismatched data ==="
    echo ""
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id,
        intro_name,
        finishedonboarding as finishedonboarding_lowercase,
        \"finishedOnboarding\" as finishedOnboarding_camelcase,
        CASE 
            WHEN finishedonboarding = \"finishedOnboarding\" THEN 'âœ… MATCH'
            WHEN finishedonboarding IS NULL AND \"finishedOnboarding\" IS NOT NULL THEN 'âš ï¸  LOWERCASE NULL'
            WHEN finishedonboarding IS NOT NULL AND \"finishedOnboarding\" IS NULL THEN 'âš ï¸  CAMELCASE NULL'
            ELSE 'âŒ MISMATCH'
        END as status
    FROM users
    WHERE finishedonboarding IS DISTINCT FROM \"finishedOnboarding\"
    ORDER BY user_id
    LIMIT 20;
    "
fi

echo ""
echo "=== Step 6: Sample users data (first 20) ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    user_id,
    intro_name,
    finishedonboarding,
    state,
    created_at,
    updated_at
FROM users
ORDER BY updated_at DESC
LIMIT 20;
"
echo ""

echo "=== Step 7: Users with finishedonboarding = false (registration not completed) ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    user_id,
    intro_name,
    finishedonboarding,
    state,
    created_at,
    updated_at
FROM users
WHERE finishedonboarding = false
ORDER BY updated_at DESC
LIMIT 20;
"
echo ""

echo "=== Step 8: Users with finishedonboarding = true (registration completed) ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    COUNT(*) as completed_registration_count
FROM users
WHERE finishedonboarding = true;
"
echo ""

echo "=== Step 9: Users with finishedonboarding = NULL ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    user_id,
    intro_name,
    finishedonboarding,
    state,
    created_at,
    updated_at
FROM users
WHERE finishedonboarding IS NULL
ORDER BY updated_at DESC
LIMIT 20;
"
echo ""

echo "=== Step 10: Quick fix - Show users who might need data recovery ==="
echo ""
if docker exec "$DB_CONTAINER" psql -U postgres -d postgres -t -c "
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
    );
" | grep -q "t"; then
    echo "Found camelCase column still exists. Checking for recovery opportunities..."
    echo ""
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        COUNT(*) as users_needing_recovery
    FROM users
    WHERE \"finishedOnboarding\" = true 
    AND (finishedonboarding = false OR finishedonboarding IS NULL);
    "
    echo ""
    echo "These users have finishedOnboarding=true but finishedonboarding=false/NULL"
    echo "They need data recovery from camelCase to lowercase column"
fi

echo ""
echo "=========================================="
echo "Diagnostic Summary"
echo "=========================================="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    'Total users' as metric,
    COUNT(*)::text as value
FROM users
UNION ALL
SELECT 
    'Users with finishedonboarding = true' as metric,
    COUNT(*)::text as value
FROM users
WHERE finishedonboarding = true
UNION ALL
SELECT 
    'Users with finishedonboarding = false' as metric,
    COUNT(*)::text as value
FROM users
WHERE finishedonboarding = false
UNION ALL
SELECT 
    'Users with finishedonboarding = NULL' as metric,
    COUNT(*)::text as value
FROM users
WHERE finishedonboarding IS NULL
UNION ALL
SELECT 
    'finishedOnboarding (camelCase) column exists' as metric,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
        ) THEN 'YES - MIGRATION INCOMPLETE!'
        ELSE 'NO - OK'
    END as value;
"
echo ""

echo "=========================================="
echo "Recommended Actions"
echo "=========================================="
echo ""

if docker exec "$DB_CONTAINER" psql -U postgres -d postgres -t -c "
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'finishedOnboarding'
    );
" | grep -q "t"; then
    echo -e "${YELLOW}âš ï¸  WARNING: finishedOnboarding (camelCase) column still exists!${NC}"
    echo ""
    echo "Action required:"
    echo "1. Re-run migration: migrate_to_finishedonboarding_lowercase.sql"
    echo ""
    echo "Or manually fix data:"
    echo "docker exec $DB_CONTAINER psql -U postgres -d postgres -c \""
    echo "UPDATE users SET finishedonboarding = \\\"finishedOnboarding\\\" WHERE \\\"finishedOnboarding\\\" IS NOT NULL;"
    echo "ALTER TABLE users DROP COLUMN IF EXISTS \\\"finishedOnboarding\\\";"
    echo "\""
    echo ""
fi

RECOVERY_COUNT=$(docker exec "$DB_CONTAINER" psql -U postgres -d postgres -t -c "
    SELECT COUNT(*) 
    FROM users
    WHERE finishedonboarding = false OR finishedonboarding IS NULL
    LIMIT 1;
" | tr -d '[:space:]')

if [ ! -z "$RECOVERY_COUNT" ] && [ "$RECOVERY_COUNT" != "0" ]; then
    echo -e "${YELLOW}âš ï¸  Found users with finishedonboarding = false/NULL${NC}"
    echo ""
    echo "If these should be true, check if data was lost during migration"
    echo "Review the sample users above and verify their registration status"
fi

echo ""
echo "=========================================="
echo "Diagnostic complete"
echo "=========================================="
