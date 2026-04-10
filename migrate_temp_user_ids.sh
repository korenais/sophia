#!/bin/bash
# Script to migrate temporary negative user_ids to real Telegram user_ids
# This should be run when users created via admin panel start interacting with the bot
# Usage: ./migrate_temp_user_ids.sh [real_user_id] [telegram_username]

REAL_USER_ID=${1}
TELEGRAM_USERNAME=${2}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables (skip comments and empty lines)
if [ -f "$SCRIPT_DIR/infra/.env" ]; then
    set -a
    # Use a more robust method to load .env file
    # Handle lines that may contain = in values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Split on first = only (key=value, where value may contain =)
        key="${line%%=*}"
        value="${line#*=}"
        # Skip if no = found
        [[ "$key" == "$line" ]] && continue
        # Trim whitespace
        key="${key%"${key##*[![:space:]]}"}"
        # Remove quotes if present
        value="${value#\"}"
        value="${value%\"}"
        value="${value#\'}"
        value="${value%\'}"
        export "$key=$value" 2>/dev/null || true
    done < "$SCRIPT_DIR/infra/.env"
    set +a
fi

DB_CONTAINER="${DB_CONTAINER:-infra_db_1}"

echo "=========================================="
echo "Migrating temporary user IDs to real IDs"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""

if [ -n "$REAL_USER_ID" ] && [ -n "$TELEGRAM_USERNAME" ]; then
    # Migrate specific user
    echo "=== Migrating user: $TELEGRAM_USERNAME -> $REAL_USER_ID ==="
    docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
    DO \$\$
    DECLARE
        temp_user RECORD;
        new_user_id INT := $REAL_USER_ID;
        new_username TEXT := '$TELEGRAM_USERNAME';
    BEGIN
        -- Find temporary user by username
        SELECT * INTO temp_user
        FROM public.users
        WHERE user_id < 0 
          AND user_telegram_link = new_username
        LIMIT 1;
        
        IF FOUND THEN
            -- Check if real user_id already exists
            IF EXISTS (SELECT 1 FROM public.users WHERE user_id = new_user_id) THEN
                RAISE NOTICE 'User with user_id % already exists. Cannot migrate.', new_user_id;
            ELSE
                -- Update user_id, preserving finishedonboarding and state
                UPDATE public.users
                SET user_id = new_user_id,
                    chat_id = new_user_id,
                    updated_at = NOW()
                WHERE user_id = temp_user.user_id;
                
                RAISE NOTICE 'Successfully migrated user from % to %', temp_user.user_id, new_user_id;
                
                -- Also update feedbacks if any
                UPDATE public.feedbacks
                SET user_id = new_user_id
                WHERE user_id = temp_user.user_id;
                
                RAISE NOTICE 'Updated feedbacks for user';
            END IF;
        ELSE
            RAISE NOTICE 'No temporary user found with username %', new_username;
        END IF;
    END \$\$;
    "
else
    # Show all temporary users that need migration
    echo "=== Temporary users that need migration ==="
    docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id as temp_id,
        intro_name,
        user_telegram_link,
        finishedonboarding,
        state,
        created_at
    FROM public.users
    WHERE user_id < 0
    ORDER BY created_at DESC;
    "
    echo ""
    echo "To migrate a specific user, run:"
    echo "  ./migrate_temp_user_ids.sh [real_telegram_user_id] [telegram_username]"
    echo ""
    echo "Example:"
    echo "  ./migrate_temp_user_ids.sh 1541686636 anton_anisim0v"
fi

echo ""
echo "=========================================="
echo "Migration check complete"
echo "=========================================="
