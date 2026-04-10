#!/bin/bash
# Script to fix missing columns in production database
# Usage: ./fix_missing_columns.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Fix Missing Database Columns"
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

# Add last_birthday_greeting_sent column
echo "=== Adding last_birthday_greeting_sent column ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') THEN
        ALTER TABLE users ADD COLUMN last_birthday_greeting_sent date;
        RAISE NOTICE 'Column last_birthday_greeting_sent added successfully';
    ELSE
        RAISE NOTICE 'Column last_birthday_greeting_sent already exists';
    END IF;
END \$\$;
"

echo ""
echo "=== Creating index for last_birthday_greeting_sent ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
CREATE INDEX IF NOT EXISTS idx_users_last_birthday_greeting ON users(last_birthday_greeting_sent);
"

echo ""
echo "=== Verification ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'last_birthday_greeting_sent';
"

echo ""
echo -e "${GREEN}âœ… All missing columns have been added!${NC}"
echo ""
echo "Note: If you have both 'finishedonboarding' and 'finishedOnboarding' columns,"
echo "      you should run fix_finishedonboarding_duplicate.sql to consolidate them."
echo ""
