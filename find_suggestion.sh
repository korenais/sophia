#!/bin/bash
# Script to find suggestion feedbacks in the database
# Usage: ./find_suggestion.sh

# Get script directory
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
        # Trim whitespace from key
        key="${key%"${key##*[![:space:]]}"}"
        key="${key#"${key%%[![:space:]]*}"}"
        # Remove quotes if present from value
        value="${value#\"}"
        value="${value%\"}"
        value="${value#\'}"
        value="${value%\'}"
        # Only export if key is not empty
        if [ -n "$key" ]; then
            export "$key=$value" 2>/dev/null || true
        fi
    done < "$SCRIPT_DIR/infra/.env"
    set +a
fi

DB_CONTAINER="${DB_CONTAINER:-infra_db_1}"

echo "=========================================="
echo "Searching for suggestion feedbacks"
echo "=========================================="

# Check if database container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "âŒ Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "âœ“ Database container is running"
echo ""

echo "=== ALL suggestion type feedbacks (type='suggestion') ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 100) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name,
    u.user_telegram_link
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
WHERE f.type = 'suggestion'
ORDER BY f.created_at DESC;
"

echo ""
echo "=== ALL feature type feedbacks (type='feature') ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 100) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name,
    u.user_telegram_link
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
WHERE f.type = 'feature'
ORDER BY f.created_at DESC;
"

echo ""
echo "=== ALL feedback types and counts ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    type,
    COUNT(*) as count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM public.feedbacks
GROUP BY type
ORDER BY type;
"

echo ""
echo "=== ALL feedbacks (full text preview, last 10) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 200) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
ORDER BY f.created_at DESC
LIMIT 10;
"

echo ""
echo "=== Search for feedbacks containing specific text (Lorem ipsum) ==="
docker exec -it "$DB_CONTAINER" psql -U postgres -d postgres -c "
SELECT 
    f.id,
    f.user_id,
    f.type,
    LEFT(f.text, 150) as message_preview,
    f.created_at,
    CASE 
        WHEN u.user_id IS NULL THEN 'USER NOT FOUND'
        ELSE COALESCE(u.intro_name, 'No name')
    END as user_name
FROM public.feedbacks f
LEFT JOIN public.users u ON u.user_id = f.user_id
WHERE LOWER(f.text) LIKE '%lorem%' 
   OR LOWER(f.text) LIKE '%ipsum%'
   OR LOWER(f.text) LIKE '%consectetur%'
ORDER BY f.created_at DESC;
"

echo ""
echo "=========================================="
echo "Search complete"
echo "=========================================="
