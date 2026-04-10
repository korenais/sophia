#!/bin/bash

# Database Dump Script for Sophia Bot
# Creates a complete database dump that can be restored manually
# Usage: ./dump_database.sh [output_file]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_CONTAINER=""
DB_NAME="postgres"
DB_USER="postgres"
BACKUP_DIR="backups"
COMPRESS=true  # Compress dump by default

# Helper function to safely parse .env file
parse_env_var() {
    local env_file="$1"
    local var_name="$2"
    
    if [ ! -f "$env_file" ]; then
        return 1
    fi
    
    # Extract value using grep and sed, removing quotes and carriage returns
    grep "^${var_name}=" "$env_file" 2>/dev/null | head -n 1 | \
        sed 's/^[^=]*=//' | \
        sed -e 's/^["'\'']//' -e 's/["'\'']$//' | \
        tr -d '\r\n'
}

# Load environment variables if .env exists (parse safely to avoid syntax errors)
if [ -f "infra/.env" ]; then
    local_user=$(parse_env_var "infra/.env" "POSTGRES_USER")
    if [ -n "$local_user" ]; then
        DB_USER="$local_user"
    fi
    
    local_db=$(parse_env_var "infra/.env" "POSTGRES_DB")
    if [ -n "$local_db" ]; then
        DB_NAME="$local_db"
    fi
fi

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
OUTPUT_FILE="$1"
if [ -z "$OUTPUT_FILE" ]; then
    # Generate default filename with timestamp
    timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    OUTPUT_FILE="${BACKUP_DIR}/sophia_dump_${timestamp}.sql"
fi

# Get absolute path for output file
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
OUTPUT_FILENAME=$(basename "$OUTPUT_FILE")

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# If output file doesn't have full path, use backup directory
if [[ "$OUTPUT_FILE" != /* ]] && [[ "$OUTPUT_FILE" != ./* ]]; then
    OUTPUT_FILE="${BACKUP_DIR}/${OUTPUT_FILENAME}"
fi

print_status "Sophia Bot Database Dump Utility"
echo ""

# Find database container
print_status "Finding database container..."
DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)

if [ -z "$DB_CONTAINER" ]; then
    print_error "Database container not found. Is the database running?"
    print_warning "Make sure Docker containers are running: cd infra && docker-compose ps"
    exit 1
fi

print_success "Database container found: $DB_CONTAINER"
print_status "Database: $DB_NAME"
print_status "User: $DB_USER"
echo ""

# Create dump
print_status "Creating database dump..."
print_status "Output file: $OUTPUT_FILE"

# Create dump using pg_dump with proper options for manual restoration
if docker exec "$DB_CONTAINER" pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --create \
    --no-owner \
    --no-privileges \
    --format=plain \
    > "$OUTPUT_FILE" 2>/dev/null; then
    
    # Verify dump file is not empty
    if [ ! -s "$OUTPUT_FILE" ]; then
        print_error "Dump file is empty! This may indicate a problem."
        rm -f "$OUTPUT_FILE"
        exit 1
    fi
    
    # Get file size before compression
    dump_size=$(du -h "$OUTPUT_FILE" | cut -f1)
    print_success "Database dump created successfully (Size: $dump_size)"
    
    # Compress if requested and gzip is available
    if [ "$COMPRESS" = true ] && command -v gzip &> /dev/null; then
        print_status "Compressing dump file..."
        gzip "$OUTPUT_FILE"
        OUTPUT_FILE="${OUTPUT_FILE}.gz"
        
        # Verify compression integrity
        if ! gzip -t "$OUTPUT_FILE" 2>/dev/null; then
            print_error "Compressed file appears to be corrupted!"
            exit 1
        fi
        
        compressed_size=$(du -h "$OUTPUT_FILE" | cut -f1)
        print_success "Dump compressed successfully (Size: $compressed_size)"
    fi
    
    # Display summary
    echo ""
    print_success "âœ… Database dump completed successfully!"
    echo ""
    echo "ðŸ“ Dump file: $OUTPUT_FILE"
    echo "ðŸ“Š File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo ""
    
    # Show restore instructions
    echo "ðŸ“– To restore this dump manually:"
    echo ""
    
    if [[ "$OUTPUT_FILE" == *.gz ]]; then
        echo "   # Method 1: Using Docker (recommended)"
        echo "   gunzip < $OUTPUT_FILE | docker exec -i $DB_CONTAINER psql -U $DB_USER"
        echo ""
        echo "   # Method 2: Extract first, then restore"
        echo "   gunzip $OUTPUT_FILE"
        echo "   docker exec -i $DB_CONTAINER psql -U $DB_USER < ${OUTPUT_FILE%.gz}"
        echo ""
        echo "   # Method 3: Using psql directly (if available locally)"
        echo "   gunzip < $OUTPUT_FILE | psql -h localhost -U $DB_USER -d postgres"
    else
        echo "   # Method 1: Using Docker (recommended)"
        echo "   docker exec -i $DB_CONTAINER psql -U $DB_USER < $OUTPUT_FILE"
        echo ""
        echo "   # Method 2: Using psql directly (if available locally)"
        echo "   psql -h localhost -U $DB_USER -d postgres < $OUTPUT_FILE"
    fi
    
    echo ""
    echo "âš ï¸  Note: The dump includes DROP and CREATE statements."
    echo "   Make sure you have a backup before restoring!"
    echo ""
    
    exit 0
else
    print_error "Failed to create database dump"
    print_warning "Check that:"
    print_warning "  1. Database container is running"
    print_warning "  2. Database credentials are correct"
    print_warning "  3. You have sufficient disk space"
    exit 1
fi
