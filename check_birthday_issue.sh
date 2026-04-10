#!/bin/bash
# Diagnostic script for birthday notification issues
# Usage: ./check_birthday_issue.sh [USER_ID]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Birthday Notification Diagnostic Tool"
echo "=========================================="
echo ""

# Get container names from docker-compose
DB_CONTAINER="infra_db_1"
BOT_CONTAINER="infra_bot_1"

# Check if containers are running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}ERROR: Database container '$DB_CONTAINER' is not running${NC}"
    exit 1
fi

echo -e "${GREEN}âœ“ Database container is running${NC}"

# Get user_id from command line or prompt
if [ -z "$1" ]; then
    echo "Enter USER_ID to check (or press Enter to check all users with birthday today):"
    read USER_ID
else
    USER_ID=$1
fi

TODAY_MONTH=$(date +%-m)  # Month without leading zero (1-12)
TODAY_DAY=$(date +%-d)    # Day without leading zero (1-31)

echo ""
echo "Today's date: $(date +%Y-%m-%d) (Month: $TODAY_MONTH, Day: $TODAY_DAY)"
echo ""

if [ -z "$USER_ID" ]; then
    echo "=== Checking all users with birthday today ==="
    echo ""
    
    # Check users with birthday today (handle both column names)
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id,
        intro_name,
        intro_birthday,
        finishedonboarding as finished_onboarding,
        finishedonboarding as finished_onboarding_value,
        last_birthday_greeting_sent,
        notifications_enabled,
        state,
        created_at
    FROM users 
    WHERE intro_birthday IS NOT NULL
    AND EXTRACT(MONTH FROM intro_birthday) = $TODAY_MONTH
    AND EXTRACT(DAY FROM intro_birthday) = $TODAY_DAY
    ORDER BY user_id;
    "
    
    echo ""
    echo "=== Users who should receive birthday greeting but haven't ==="
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id,
        intro_name,
        intro_birthday,
        finishedonboarding as finished_onboarding,
        last_birthday_greeting_sent,
        CASE 
            WHEN finishedonboarding = true THEN 'OK'
            ELSE 'NOT FINISHED ONBOARDING'
        END as onboarding_status,
        CASE 
            WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
                THEN 'COLUMN NOT EXISTS'
            WHEN last_birthday_greeting_sent IS NULL THEN 'NOT SENT YET'
            WHEN last_birthday_greeting_sent::date = CURRENT_DATE THEN 'ALREADY SENT TODAY'
            ELSE 'SENT PREVIOUSLY: ' || last_birthday_greeting_sent::date::text
        END as greeting_status
    FROM users 
    WHERE intro_birthday IS NOT NULL
    AND EXTRACT(MONTH FROM intro_birthday) = $TODAY_MONTH
    AND EXTRACT(DAY FROM intro_birthday) = $TODAY_DAY
    AND (finishedonboarding = false 
         OR last_birthday_greeting_sent IS NOT NULL)
    ORDER BY user_id;
    "
else
    echo "=== Checking user ID: $USER_ID ==="
    echo ""
    
    # Get full user info (handle missing last_birthday_greeting_sent column)
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id,
        intro_name,
        intro_birthday,
        EXTRACT(MONTH FROM intro_birthday) as birthday_month,
        EXTRACT(DAY FROM intro_birthday) as birthday_day,
        finishedonboarding as finished_onboarding_effective,
        CASE 
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
            THEN last_birthday_greeting_sent::text
            ELSE 'COLUMN NOT EXISTS'
        END as last_birthday_greeting_sent,
        notifications_enabled,
        state,
        created_at,
        updated_at
    FROM users 
    WHERE user_id = $USER_ID;
    "
    
    echo ""
    echo "=== Birthday check results ==="
    docker exec "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        CASE 
            WHEN intro_birthday IS NULL THEN 'âŒ No birthday set'
            WHEN EXTRACT(MONTH FROM intro_birthday) != $TODAY_MONTH OR EXTRACT(DAY FROM intro_birthday) != $TODAY_DAY 
                THEN 'âŒ Birthday is NOT today (it is ' || intro_birthday::text || ')'
            WHEN finishedonboarding != true 
                THEN 'âŒ finishedonboarding is NOT true (value: ' || COALESCE(finishedonboarding::text, 'NULL') || ')'
            WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
                THEN 'âš ï¸  Column last_birthday_greeting_sent does not exist - need to run migration'
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
                AND last_birthday_greeting_sent::date = CURRENT_DATE THEN 'âš ï¸  Greeting already sent today (' || last_birthday_greeting_sent::text || ')'
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
                AND last_birthday_greeting_sent IS NULL THEN 'âœ… Should receive greeting (not sent yet)'
            WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_birthday_greeting_sent') 
                THEN 'âš ï¸  Greeting was sent previously on ' || last_birthday_greeting_sent::date::text
            ELSE 'âœ… Should receive greeting (column exists but value is NULL)'
        END as status
    FROM users 
    WHERE user_id = $USER_ID;
    "
fi

echo ""
echo "=== Bot configuration check ==="
echo ""
if docker ps | grep -q "$BOT_CONTAINER"; then
    echo "BIRTHDAYS setting:"
    docker exec "$BOT_CONTAINER" printenv BIRTHDAYS || echo "BIRTHDAYS not set"
    
    echo ""
    echo "BIRTHDAY_TOPIC_ID setting:"
    docker exec "$BOT_CONTAINER" printenv BIRTHDAY_TOPIC_ID || echo "BIRTHDAY_TOPIC_ID not set"
    
    echo ""
    echo "TELEGRAM_GROUP_ID setting:"
    docker exec "$BOT_CONTAINER" printenv TELEGRAM_GROUP_ID || echo "TELEGRAM_GROUP_ID not set"
else
    echo -e "${YELLOW}âš  Bot container '$BOT_CONTAINER' is not running - cannot check environment variables${NC}"
fi

echo ""
echo "=== Recent bot logs (birthday related) ==="
echo ""
if docker ps | grep -q "$BOT_CONTAINER"; then
    docker logs "$BOT_CONTAINER" --tail 100 2>&1 | grep -i "birthday\|greeting" | tail -20 || echo "No birthday-related logs found in last 100 lines"
else
    echo -e "${YELLOW}âš  Bot container is not running${NC}"
fi

echo ""
echo "=== Scheduled jobs status ==="
echo ""
if docker ps | grep -q "$BOT_CONTAINER"; then
    docker logs "$BOT_CONTAINER" --tail 500 2>&1 | grep -i "check_recently_updated_birthdays\|check_birthday_greetings\|birthday.*job\|scheduler" | tail -10 || echo "No scheduler logs found"
fi

echo ""
echo "=== Quick fix commands ==="
echo ""
if [ ! -z "$USER_ID" ]; then
    echo "# To reset last_birthday_greeting_sent for user $USER_ID (allows re-sending):"
    echo "docker exec $DB_CONTAINER psql -U postgres -d postgres -c \"UPDATE users SET last_birthday_greeting_sent = NULL WHERE user_id = $USER_ID;\""
    echo ""
    echo "# To set finishedonboarding = true for user $USER_ID:"
    echo "docker exec $DB_CONTAINER psql -U postgres -d postgres -c \"UPDATE users SET finishedonboarding = true WHERE user_id = $USER_ID;\""
    echo ""
    echo "# To manually trigger birthday check via bot (if bot container is running):"
    echo "docker exec $BOT_CONTAINER python3 -c \"from birthday_greetings import check_birthday_for_user; import asyncio; from aiogram import Bot; import asyncpg; import os; async def main(): bot = Bot(token=os.getenv('TELEGRAM_TOKEN')); pool = await asyncpg.create_pool(os.getenv('DB_URL')); result = await check_birthday_for_user(bot, pool, $USER_ID); print('Result:', result); await pool.close(); asyncio.run(main())\""
fi

echo ""
echo "=========================================="
echo "Diagnostic complete"
echo "=========================================="
