#!/bin/bash
# Script to check why bot container exited
# Usage: ./check_bot_exit.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables (skip comments and empty lines)
if [ -f "$SCRIPT_DIR/infra/.env" ]; then
    set -a
    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        [[ "$key" == "$line" ]] && continue
        key="${key%"${key##*[![:space:]]}"}"
        key="${key#"${key%%[![:space:]]*}"}"
        value="${value#\"}"
        value="${value%\"}"
        value="${value#\'}"
        value="${value%\'}"
        if [ -n "$key" ]; then
            export "$key=$value" 2>/dev/null || true
        fi
    done < "$SCRIPT_DIR/infra/.env"
    set +a
fi

echo "=========================================="
echo "Checking bot container exit reason"
echo "=========================================="

# Find bot container (including stopped ones)
BOT_CONTAINER=$(docker ps -a --format "{{.Names}}" | grep -E "(bot|sophia.*bot)" | head -n 1)

if [ -z "$BOT_CONTAINER" ]; then
    echo "âŒ Bot container not found"
    echo "Available containers:"
    docker ps -a --format "{{.Names}}"
    exit 1
fi

echo "âœ“ Bot container found: $BOT_CONTAINER"
echo ""

# Check container status
echo "=== Container Status ==="
docker ps -a --filter "name=$BOT_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.ExitCode}}"
echo ""

# Get last 100 lines of logs
echo "=== Last 100 lines of bot logs ==="
docker logs "$BOT_CONTAINER" --tail 100 2>&1
echo ""

# Get error lines specifically
echo "=== Error lines from bot logs ==="
docker logs "$BOT_CONTAINER" 2>&1 | grep -i "error\|exception\|traceback\|failed\|fatal" | tail -20 || echo "No error lines found"
echo ""

echo "=========================================="
echo "Check complete"
echo "=========================================="
