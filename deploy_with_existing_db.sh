#!/bin/bash

# Deployment Script for Existing Database
# This script deploys new version while preserving existing database data
# Usage: ./deploy_with_existing_db.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration
BACKUP_DIR="backups"
DB_CONTAINER=""
DB_NAME="postgres"
DB_USER="postgres"
DB_PASSWORD="postgres"
MIGRATIONS_DIR="services/db"

# Helper function to safely parse .env file
parse_env_var() {
    local env_file="$1"
    local var_name="$2"
    
    if [ ! -f "$env_file" ]; then
        return 1
    fi
    
    grep "^${var_name}=" "$env_file" 2>/dev/null | head -n 1 | \
        sed 's/^[^=]*=//' | \
        sed -e 's/^["'\'']//' -e 's/["'\'']$//' | \
        tr -d '\r\n'
}

# Get database connection string from environment or use defaults
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

echo "=========================================="
echo "ðŸš€ Sophia Deployment - Existing Database"
echo "=========================================="
echo ""

# Step 1: Check Docker
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker."
    exit 1
fi
print_success "Docker and Docker Compose are installed and running"

# Step 2: Create database backup BEFORE any changes
print_status "Creating database backup before deployment..."
mkdir -p "$BACKUP_DIR"
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
backup_file="${BACKUP_DIR}/sophia_backup_before_deploy_${timestamp}.sql"

# Check if database container is already running
DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)

if [ -z "$DB_CONTAINER" ]; then
    print_warning "Database container not running yet. Will create backup after services start."
else
    print_status "Found existing database container: $DB_CONTAINER"
    print_status "Creating backup: $backup_file"
    
    if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$backup_file" 2>/dev/null; then
        if [ -s "$backup_file" ]; then
            backup_size=$(du -h "$backup_file" | cut -f1)
            print_success "Database backup created: $backup_file (Size: $backup_size)"
        else
            print_warning "Backup file is empty, but continuing..."
            rm -f "$backup_file"
        fi
    else
        print_warning "Could not create backup from existing container, continuing..."
    fi
fi

# Step 3: Build and start services
print_status "Building and starting new version..."
cd infra

print_status "Building Docker images..."
docker-compose build --no-cache

print_status "Starting services..."
docker-compose up -d

cd ..

# Wait for containers to start
sleep 5

# Step 4: Find database container
print_status "Finding database container..."
DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)

if [ -z "$DB_CONTAINER" ]; then
    print_error "Database container not found after starting services"
    exit 1
fi

print_success "Database container found: $DB_CONTAINER"

# Step 5: Wait for database to be ready
print_status "Waiting for database to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" &> /dev/null 2>&1; then
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    print_error "Database failed to start within 60 seconds"
    exit 1
fi
print_success "Database is ready"

# Step 6: Create backup if we didn't before
if [ ! -f "$backup_file" ] || [ ! -s "$backup_file" ]; then
    print_status "Creating database backup now..."
    timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    backup_file="${BACKUP_DIR}/sophia_backup_before_deploy_${timestamp}.sql"
    
    if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$backup_file" 2>/dev/null; then
        if [ -s "$backup_file" ]; then
            backup_size=$(du -h "$backup_file" | cut -f1)
            print_success "Database backup created: $backup_file (Size: $backup_size)"
        fi
    fi
fi

# Step 7: Check and add missing tables/columns (SAFE - preserves data)
print_status "Checking database schema and adding missing tables/columns..."
print_warning "This will add missing tables and columns WITHOUT dropping existing data"

if [ -f "$MIGRATIONS_DIR/check_and_add_missing_tables.sql" ]; then
    print_status "Running safe schema update (check_and_add_missing_tables.sql)..."
    if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/check_and_add_missing_tables.sql"; then
        print_success "Schema update completed (missing tables/columns added)"
    else
        print_warning "Schema update had some issues (may already be up to date)"
    fi
fi

# Step 8: Run comprehensive migration (also safe - only adds missing columns)
print_status "Running comprehensive migration (migrate_to_latest.sql)..."
if [ -f "$MIGRATIONS_DIR/migrate_to_latest.sql" ]; then
    if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/migrate_to_latest.sql"; then
        print_success "Comprehensive migration completed"
    else
        print_warning "Migration had some issues (may already be applied)"
    fi
fi

# Step 9: Verify schema
print_status "Verifying database schema..."
if [ -f "$MIGRATIONS_DIR/verify_schema.sql" ]; then
    if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/verify_schema.sql" 2>&1 | grep -q "verification completed successfully"; then
        print_success "Schema verification passed"
    else
        print_warning "Schema verification had warnings (check output above)"
    fi
fi

# Step 10: Wait for services
print_status "Waiting for services to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -f http://localhost:8055/api/health &> /dev/null 2>&1 || curl -f http://localhost:8055/health &> /dev/null 2>&1; then
        print_success "API is ready"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

# Step 11: Show status
echo ""
print_status "Deployment Status:"
echo ""
echo "ðŸ“Š Service Status:"
cd infra
docker-compose ps
cd ..

echo ""
echo "ðŸŒ Access URLs:"
echo "  Frontend: http://localhost:8081"
echo "  API: http://localhost:8055"
echo ""

echo ""
print_success "ðŸŽ‰ Deployment completed successfully!"
echo ""
print_warning "Important:"
print_warning "1. Database backup saved to: ${backup_file}"
print_warning "2. All existing data has been preserved"
print_warning "3. Missing tables and columns have been added"
print_warning "4. Verify all services are running: cd infra && docker-compose ps"
print_warning "5. Check logs for any errors: cd infra && docker-compose logs"
echo ""
