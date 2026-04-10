#!/bin/bash
# Script to check and migrate feedbacks from temporary user_ids to real user_ids
# Usage: ./check_migrate_feedbacks.sh

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
echo "Checking feedbacks with temporary user_ids"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""

echo "=== Feedbacks with temporary user_ids (negative) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 100) as message_preview,
    f.created_at,
    u.intro_name,
    u.user_telegram_link
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
WHERE f.user_id < 0
ORDER BY f.created_at DESC;
"

echo ""
echo "=== All feedbacks (recent 20) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 80) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
ORDER BY f.created_at DESC
LIMIT 20;
"

echo ""
echo "=== Temporary users that might need feedback migration ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    u.user_id as temp_id,
    u.intro_name,
    u.user_telegram_link,
    (SELECT COUNT(*) FROM public.feedbacks f WHERE f.user_id = u.user_id) as feedback_count
FROM public.users u
WHERE u.user_id < 0
ORDER BY u.created_at DESC;
"

echo ""
echo "=========================================="
echo "Check complete"
echo "=========================================="
echo ""
echo "If you see feedbacks with negative user_ids, they need to be migrated."
echo "Use migrate_temp_user_ids.sh to migrate specific users."
echo "The middleware should handle this automatically for new feedbacks."
