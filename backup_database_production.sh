#!/bin/bash

# Production Database Backup Script for Sophia Bot
# This script creates a comprehensive backup of the production database
# Usage: ./backup_database_production.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups"
DB_CONTAINER=""
DB_NAME="postgres"
DB_USER="postgres"
DB_PASSWORD="postgres"
RETENTION_DAYS=30  # Keep backups for 30 days

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
    local_password=$(parse_env_var "infra/.env" "POSTGRES_PASSWORD")
    if [ -n "$local_password" ]; then
        DB_PASSWORD="$local_password"
    fi
    
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

# Find database container
print_status "Finding database container..."
DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)

if [ -z "$DB_CONTAINER" ]; then
    print_error "Database container not found. Is the database running?"
    exit 1
fi

print_success "Database container found: $DB_CONTAINER"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Get current date and time for backup filename
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
backup_file="${BACKUP_DIR}/sophia_backup_${timestamp}.sql"
backup_file_compressed="${backup_file}.gz"

print_status "Creating database backup..."
print_status "Backup file: $backup_file"

# Create database backup using pg_dump
if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$backup_file" 2>/dev/null; then
    # Verify backup file is not empty
    if [ ! -s "$backup_file" ]; then
        print_error "Backup file is empty! This may indicate a problem."
        rm -f "$backup_file"
        exit 1
    fi
    
    # Compress backup
    print_status "Compressing backup..."
    if command -v gzip &> /dev/null; then
        gzip "$backup_file"
        backup_file="$backup_file_compressed"
        print_success "Backup compressed"
    fi
    
    backup_size=$(du -h "$backup_file" | cut -f1)
    print_success "Database backup created successfully: $backup_file (Size: $backup_size)"
    
    # Verify backup integrity by checking if it can be read
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>/dev/null; then
            print_error "Backup file appears to be corrupted!"
            exit 1
        fi
    fi
    
    # Clean up old backups
    print_status "Cleaning old backups (keeping last $RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -name "sophia_backup_*.sql*" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    # Also keep only last 10 backups regardless of age
    print_status "Keeping only last 10 backups..."
    ls -t "$BACKUP_DIR"/sophia_backup_*.sql* 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    
    print_success "Backup cleanup completed"
    
    echo ""
    print_success "âœ… Database backup completed successfully!"
    echo ""
    echo "ðŸ“ Backup location: $backup_file"
    echo "ðŸ“Š Backup size: $backup_size"
    echo ""
    echo "ðŸ’¡ To restore from this backup:"
    if [[ "$backup_file" == *.gz ]]; then
        echo "   gunzip < $backup_file | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME"
    else
        echo "   docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME < $backup_file"
    fi
    echo ""
    
    exit 0
else
    print_error "Failed to create database backup"
    exit 1
fi
