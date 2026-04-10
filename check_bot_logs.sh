#!/bin/bash
# Script to check bot logs for suggestions and feedbacks
# Usage: ./check_bot_logs.sh [search_term]

SEARCH_TERM="${1:-suggest\|feedback\|999000111}"
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

echo "=========================================="
echo "Checking bot logs for: $SEARCH_TERM"
echo "=========================================="

# Find bot container
BOT_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(bot|sophia.*bot)" | head -n 1)

if [ -z "$BOT_CONTAINER" ]; then
    echo "âŒ Bot container not found"
    echo "Available containers:"
    docker ps --format "{{.Names}}"
    exit 1
fi

echo "âœ“ Bot container found: $BOT_CONTAINER"
echo ""

echo "=== Recent bot logs - last 200 lines, filtered ==="
docker logs "$BOT_CONTAINER" --tail 200 2>&1 | grep -i "$SEARCH_TERM" || echo "No matches found in recent logs"

echo ""
echo "=== All bot logs - filtered, last 50 matches ==="
docker logs "$BOT_CONTAINER" 2>&1 | grep -i "$SEARCH_TERM" | tail -50 || echo "No matches found"

echo ""
echo "=========================================="
echo "Log check complete"
echo "=========================================="
echo ""
echo "To see all recent logs:"
echo "  docker logs $BOT_CONTAINER --tail 100"
echo ""
echo "To monitor logs in real-time:"
echo "  docker logs -f $BOT_CONTAINER"
