#!/bin/bash
# Script to check user status and diagnose registration/matching issues
# Usage: ./check_user_status.sh [user_id]

USER_ID=${1:-1541686636}
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
echo "Checking user status in database"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""
echo "=== User information for user_id: $USER_ID ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    user_id,
    chat_id,
    intro_name,
    user_telegram_link,
    finishedonboarding,
    state,
    CASE 
        WHEN intro_description IS NULL THEN 'NULL'
        WHEN length(trim(intro_description)) < 10 THEN 'TOO SHORT (' || length(trim(intro_description)) || ' chars)'
        ELSE 'OK (' || length(trim(intro_description)) || ' chars)'
    END as description_status,
    CASE 
        WHEN vector_description IS NULL THEN 'NULL'
        ELSE 'EXISTS (' || array_length(vector_description, 1) || ' dimensions)'
    END as vector_status,
    created_at,
    updated_at
FROM public.users
WHERE user_id = $USER_ID;
"

echo ""
echo "=== Check for temporary user_id (negative) ==="
if [ "$USER_ID" -gt 0 ]; then
    docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
    SELECT 
        user_id,
        intro_name,
        user_telegram_link,
        finishedonboarding,
        state
    FROM public.users
    WHERE user_id < 0
    ORDER BY created_at DESC
    LIMIT 5;
    "
fi

echo ""
echo "=== Feedback records for user_id: $USER_ID ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    id,
    user_id,
    type,
    LEFT(text, 100) as message_preview,
    created_at
FROM public.feedbacks
WHERE user_id = $USER_ID
ORDER BY created_at DESC;
"

echo ""
echo "=========================================="
echo "Check complete"
echo "=========================================="
