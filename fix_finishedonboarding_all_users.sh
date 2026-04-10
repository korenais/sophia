#!/bin/bash
# Script to set finishedonboarding = true for all users
# Usage: ./fix_finishedonboarding_all_users.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Fix finishedonboarding for all users"
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

echo "=== Current status ==="
echo ""
docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    finishedonboarding,
    COUNT(*) as user_count
FROM users
GROUP BY finishedonboarding
ORDER BY finishedonboarding NULLS LAST;
"
echo ""

echo -e "${YELLOW}This will set finishedonboarding = true for ALL users${NC}"
echo -e "${YELLOW}Press Ctrl+C to cancel, or Enter to continue...${NC}"
read -r

echo ""
echo "=== Updating all users to finishedonboarding = true ==="
echo ""

docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
UPDATE users 
SET finishedonboarding = true, updated_at = NOW()
WHERE finishedonboarding = false OR finishedonboarding IS NULL;
"

echo ""
echo "=== Verification ==="
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

echo -e "${GREEN}=========================================="
echo "Update completed successfully!"
echo "==========================================${NC}"
echo ""
