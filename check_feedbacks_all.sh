#!/bin/bash
# Script to check all feedbacks, especially those with temporary user_ids
# Usage: ./check_feedbacks_all.sh

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
echo "Checking ALL feedbacks in database"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""

echo "=== ALL feedbacks (ordered by created_at DESC) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 60) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
ORDER BY f.created_at DESC;
"

echo ""
echo "=== Feedbacks with temporary user_ids (negative) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 80) as message_preview,
    f.created_at,
    u.intro_name,
    u.user_telegram_link
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
WHERE f.user_id < 0
ORDER BY f.created_at DESC;
"

echo ""
echo "=== Count by type ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    type,
    COUNT(*) as count
FROM public.feedbacks
GROUP BY type
ORDER BY type;
"

echo ""
echo "=========================================="
echo "Check complete"
echo "=========================================="
