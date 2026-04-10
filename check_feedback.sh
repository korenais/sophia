#!/bin/bash
# Script to check feedback records in the database
# Usage: ./check_feedback.sh [user_id]

USER_ID=${1:-999000111}
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
echo "Checking feedback records in database"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""
echo "=== All feedbacks for user_id: $USER_ID ==="
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
echo "=== Total feedback count ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT COUNT(*) as total_feedbacks FROM public.feedbacks;
"

echo ""
echo "=== Recent feedbacks (last 20) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    id,
    user_id,
    type,
    LEFT(text, 80) as message_preview,
    created_at
FROM public.feedbacks
ORDER BY created_at DESC
LIMIT 20;
"

echo ""
echo "=== Check if user exists ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    user_id,
    intro_name,
    state,
    created_at
FROM public.users
WHERE user_id = $USER_ID;
"

echo ""
echo "=========================================="
echo "Check complete"
echo "=========================================="
