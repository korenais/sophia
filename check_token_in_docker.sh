#!/bin/bash

# Script to check if TELEGRAM_TOKEN is properly passed to Docker container
# Usage: ./check_token_in_docker.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Checking TELEGRAM_TOKEN in Docker"
echo "=========================================="

# Load .env file from infra directory
if [ ! -f "infra/.env" ]; then
    echo "ERROR: infra/.env file not found!"
    exit 1
fi

echo ""
echo "=== Step 1: Checking .env file ==="
if grep -q "^TELEGRAM_TOKEN=" "infra/.env"; then
    echo "âœ“ TELEGRAM_TOKEN found in infra/.env"
    
    # Extract token value (handle quotes)
    TOKEN_FROM_ENV=$(grep "^TELEGRAM_TOKEN=" "infra/.env" | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//" | xargs)
    
    if [ -z "$TOKEN_FROM_ENV" ]; then
        echo "ERROR: TELEGRAM_TOKEN is empty in .env file!"
        exit 1
    fi
    
    TOKEN_LENGTH=${#TOKEN_FROM_ENV}
    echo "  Token length: $TOKEN_LENGTH characters"
    
    # Check for spaces
    if [[ "$TOKEN_FROM_ENV" =~ [[:space:]] ]]; then
        echo "  WARNING: Token contains spaces!"
        echo "  Token preview (first 20 chars): ${TOKEN_FROM_ENV:0:20}..."
    else
        echo "  âœ“ Token does not contain spaces"
    fi
    
    # Check for leading/trailing whitespace
    TRIMMED=$(echo "$TOKEN_FROM_ENV" | xargs)
    if [ "$TOKEN_FROM_ENV" != "$TRIMMED" ]; then
        echo "  WARNING: Token has leading/trailing whitespace!"
        echo "  Original length: $TOKEN_LENGTH"
        echo "  Trimmed length: ${#TRIMMED}"
    else
        echo "  âœ“ Token has no leading/trailing whitespace"
    fi
else
    echo "ERROR: TELEGRAM_TOKEN not found in infra/.env file!"
    exit 1
fi

echo ""
echo "=== Step 2: Checking docker-compose.yml configuration ==="
if grep -q "TELEGRAM_TOKEN.*\${TELEGRAM_TOKEN}" "infra/docker-compose.yml"; then
    echo "âœ“ docker-compose.yml correctly references \${TELEGRAM_TOKEN}"
else
    echo "ERROR: docker-compose.yml does not reference TELEGRAM_TOKEN correctly!"
    exit 1
fi

echo ""
echo "=== Step 3: Checking what docker-compose sees (dry-run) ==="
cd infra
if docker-compose config 2>/dev/null | grep -A 2 "TELEGRAM_TOKEN" > /dev/null; then
    echo "âœ“ docker-compose can read TELEGRAM_TOKEN"
    echo ""
    echo "Resolved TELEGRAM_TOKEN value (from docker-compose config):"
    docker-compose config 2>/dev/null | grep -A 2 "TELEGRAM_TOKEN" | head -3 | sed 's/^/  /'
    
    # Extract resolved token
    RESOLVED_TOKEN=$(docker-compose config 2>/dev/null | grep "TELEGRAM_TOKEN:" | awk '{print $2}' | sed 's/^"//;s/"$//')
    RESOLVED_LENGTH=${#RESOLVED_TOKEN}
    echo ""
    echo "  Resolved token length: $RESOLVED_LENGTH characters"
    
    if [ "$RESOLVED_LENGTH" -eq 0 ]; then
        echo "  ERROR: docker-compose resolved token to empty string!"
        echo "  This means .env variable is not being loaded correctly"
    elif [[ "$RESOLVED_TOKEN" =~ [[:space:]] ]]; then
        echo "  WARNING: Resolved token contains spaces!"
    fi
else
    echo "ERROR: docker-compose cannot read TELEGRAM_TOKEN"
    exit 1
fi
cd ..

echo ""
echo "=== Step 4: Checking bot container environment (if running) ==="
BOT_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(bot|sophia.*bot)" | head -n 1)

if [ -z "$BOT_CONTAINER" ]; then
    echo "âš  Bot container is not running. Cannot check container environment."
    echo "  Start the container first: cd infra && docker-compose up -d"
else
    echo "âœ“ Found bot container: $BOT_CONTAINER"
    
    CONTAINER_TOKEN=$(docker exec "$BOT_CONTAINER" env | grep "^TELEGRAM_TOKEN=" | cut -d '=' -f2- || echo "")
    
    if [ -z "$CONTAINER_TOKEN" ]; then
        echo "  ERROR: TELEGRAM_TOKEN not found in container environment!"
    else
        CONTAINER_TOKEN_LENGTH=${#CONTAINER_TOKEN}
        echo "  âœ“ TELEGRAM_TOKEN found in container"
        echo "  Token length in container: $CONTAINER_TOKEN_LENGTH characters"
        
        if [[ "$CONTAINER_TOKEN" =~ [[:space:]] ]]; then
            echo "  ERROR: Token in container contains spaces!"
            echo "  This is the root cause of the validation error!"
        else
            echo "  âœ“ Token in container does not contain spaces"
        fi
        
        # Compare with .env
        if [ "$CONTAINER_TOKEN" != "$TOKEN_FROM_ENV" ]; then
            echo "  WARNING: Container token differs from .env token!"
            echo "  .env length: $TOKEN_LENGTH"
            echo "  Container length: $CONTAINER_TOKEN_LENGTH"
        else
            echo "  âœ“ Container token matches .env token"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "Check complete"
echo "=========================================="
