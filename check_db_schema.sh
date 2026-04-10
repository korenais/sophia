#!/bin/bash
# Script to check database schema - all columns in users table
# Usage: ./check_db_schema.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Database Schema Check"
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

echo "=== All columns in users table ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "\d users"
echo ""

echo "=== Checking for newly added columns ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name IN ('notifications_enabled', 'matches_disabled', 'last_birthday_greeting_sent') 
        THEN 'âœ¨ NEW COLUMN'
        WHEN column_name = 'finishedonboarding'
        THEN 'âš ï¸  ONBOARDING COLUMN'
        ELSE ''
    END as status
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'users'
ORDER BY ordinal_position;
"
echo ""

echo "=== Specific checks for new columns ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    'notifications_enabled' as column_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') 
        THEN 'âœ… EXISTS'
        ELSE 'âŒ MISSING'
    END as status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled') 
        THEN (SELECT data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_enabled')
        ELSE 'N/A'
    END as data_type
UNION ALL
SELECT 
    'matches_disabled' as column_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') 
        THEN 'âœ… EXISTS'
        ELSE 'âŒ MISSING'
    END as status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled') 
        THEN (SELECT data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'matches_disabled')
        ELSE 'N/A'
    END as data_type
UNION ALL
SELECT 
    'last_birthday_greeting_sent' as column_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
        THEN 'âœ… EXISTS'
        ELSE 'âŒ MISSING'
    END as status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
        THEN (SELECT data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent')
        ELSE 'N/A'
    END as data_type
UNION ALL
SELECT 
    'finishedonboarding (lowercase)' as column_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
        THEN 'âœ… EXISTS'
        ELSE 'âŒ MISSING'
    END as status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
        THEN (SELECT data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding')
        ELSE 'N/A'
    END as data_type
UNION ALL
SELECT 
    'finishedonboarding' as column_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
        THEN 'âœ… EXISTS'
        ELSE 'âŒ MISSING'
    END as status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding') 
        THEN (SELECT data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'finishedonboarding')
        ELSE 'N/A'
    END as data_type;
"
echo ""

echo "=== Indexes on users table ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename = 'users'
ORDER BY indexname;
"
echo ""

echo "=== Checking notifications table columns ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'notifications'
ORDER BY ordinal_position;
" || echo -e "${YELLOW}âš  Notifications table does not exist${NC}"
echo ""

echo "=========================================="
echo "Schema check complete"
echo "=========================================="
