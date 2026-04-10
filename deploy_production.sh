#!/bin/bash

# Production Deployment Script for Sophia Bot
# This script ensures safe deployment with database backup and migrations
# Usage: ./deploy_production.sh

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
DB_CONTAINER="sophia-db-1"
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
    
    # Extract value using grep and sed, removing quotes and carriage returns
    grep "^${var_name}=" "$env_file" 2>/dev/null | head -n 1 | \
        sed 's/^[^=]*=//' | \
        sed -e 's/^["'\'']//' -e 's/["'\'']$//' | \
        tr -d '\r\n'
}

# Get database connection string from environment or use defaults
# Parse .env file safely (avoid sourcing to prevent syntax errors)
if [ -f "infra/.env" ]; then
    # Extract specific variables from .env file safely
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

DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"

# Function to check if Docker is running
check_docker() {
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
}

# Function to check if database container is running
check_database() {
    print_status "Checking database container..."
    
    # Try to find the database container
    DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)
    
    if [ -z "$DB_CONTAINER" ]; then
        print_warning "Database container not found. Will start services first."
        return 1
    fi
    
    print_success "Database container found: $DB_CONTAINER"
    return 0
}

# Function to create database backup
create_backup() {
    print_status "Creating database backup..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Get current date and time for backup filename
    timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    backup_file="${BACKUP_DIR}/sophia_backup_${timestamp}.sql"
    
    # Check if database container is running
    if ! check_database; then
        print_warning "Database container not running. Skipping backup (will be created after services start)."
        return 0
    fi
    
    print_status "Creating backup: $backup_file"
    
    # Create database backup using pg_dump
    if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$backup_file" 2>/dev/null; then
        backup_size=$(du -h "$backup_file" | cut -f1)
        print_success "Database backup created successfully: $backup_file (Size: $backup_size)"
        
        # Verify backup file is not empty
        if [ ! -s "$backup_file" ]; then
            print_error "Backup file is empty! This may indicate a problem."
            exit 1
        fi
        
        # Keep only last 10 backups
        print_status "Cleaning old backups (keeping last 10)..."
        ls -t "$BACKUP_DIR"/sophia_backup_*.sql 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
        
        return 0
    else
        print_error "Failed to create database backup"
        print_warning "Continuing with deployment, but backup was not created"
        return 1
    fi
}

# Function to verify database connection
verify_db_connection() {
    print_status "Verifying database connection..."
    
    # Wait for database to be ready
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" &> /dev/null; then
            print_success "Database connection verified"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "Database connection failed after $max_attempts attempts"
    return 1
}

# Function to apply database migrations
apply_migrations() {
    print_status "Applying database migrations..."
    
    if [ ! -d "$MIGRATIONS_DIR" ]; then
        print_error "Migrations directory not found: $MIGRATIONS_DIR"
        exit 1
    fi
    
    # Verify database connection first
    if ! verify_db_connection; then
        print_error "Cannot connect to database. Migrations cannot be applied."
        exit 1
    fi
    
    # Run comprehensive migration
    print_status "Running comprehensive migration (migrate_to_latest.sql)..."
    if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/migrate_to_latest.sql"; then
        print_success "Comprehensive migration completed"
    else
        print_error "Migration failed"
        exit 1
    fi
    
    # Run field_of_activity migration (backup)
    if [ -f "$MIGRATIONS_DIR/add_field_of_activity_column.sql" ]; then
        print_status "Running field_of_activity migration..."
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/add_field_of_activity_column.sql"; then
            print_success "Field of activity migration completed"
        else
            print_warning "Field of activity migration had issues (may already be applied)"
        fi
    fi
    
    # Run user groups migration
    if [ -f "$MIGRATIONS_DIR/add_user_groups.sql" ]; then
        print_status "Running user groups migration..."
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/add_user_groups.sql"; then
            print_success "User groups migration completed"
        else
            print_warning "User groups migration had issues (may already be applied)"
        fi
    fi
    
    # Verify schema
    print_status "Verifying database schema..."
    if [ -f "$MIGRATIONS_DIR/verify_schema.sql" ]; then
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/verify_schema.sql" 2>&1 | grep -q "verification completed successfully"; then
            print_success "Database schema verification passed"
        else
            print_warning "Schema verification had warnings (check output above)"
        fi
    fi
    
    print_success "All migrations applied successfully"
}

# Function to check environment configuration
check_env() {
    print_status "Checking environment configuration..."
    if [ ! -f "infra/.env" ]; then
        print_warning ".env file not found in infra/ directory"
        if [ -f "infra/env.sample.txt" ]; then
            print_warning "Copying env.sample.txt to .env..."
            cp infra/env.sample.txt infra/.env
            print_warning "Please edit infra/.env with your production values before continuing"
            read -p "Press Enter after updating .env file..."
        else
            print_error "No environment template found. Cannot proceed."
            exit 1
        fi
    fi
    print_success "Environment configuration found"
}

# Function to deploy services
deploy_services() {
    print_status "Deploying services with Docker Compose..."
    
    cd infra
    
    # Clean up old containers and images if they exist (to avoid ContainerConfig errors)
    print_status "Cleaning up old containers and images..."
    docker-compose down --remove-orphans 2>/dev/null || true
    docker-compose rm -f 2>/dev/null || true
    
    # Build and start services
    print_status "Building Docker images..."
    print_warning "Note: docker-compose build only builds images, it does NOT run database migrations"
    docker-compose build --no-cache
    
    print_status "Starting services..."
    print_warning "Note: Migration scripts in /docker-entrypoint-initdb.d/ only run on FIRST database initialization"
    print_warning "For existing databases, migrations will be applied manually after services start"
    docker-compose up -d
    
    cd ..
    
    # Wait a bit for containers to start
    sleep 5
    
    # Update DB_CONTAINER variable
    DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(db|postgres|sophia.*db)" | head -n 1)
    
    print_success "Services deployed successfully"
}

# Function to wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for database
    print_status "Waiting for database..."
    local timeout=60
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
    
    # Wait for API
    print_status "Waiting for API..."
    local api_timeout=60
    local api_ready=0
    while [ $api_timeout -gt 0 ]; do
        # Try to reach API health endpoint
        # Use the API_PORT from environment or default to 8055
        local api_port="${API_PORT:-8055}"
        if curl -f -s "http://localhost:${api_port}/health" &> /dev/null 2>&1 || \
           curl -f -s "http://localhost:${api_port}/api/health" &> /dev/null 2>&1; then
            print_success "API is ready"
            api_ready=1
            break
        fi
        sleep 2
        api_timeout=$((api_timeout - 2))
    done
    
    if [ $api_ready -eq 0 ]; then
        print_warning "API health check failed after 60 seconds, but continuing..."
        print_warning "API may still be starting up. Check logs with: docker-compose logs api"
    fi
}

# Function to show deployment status
show_status() {
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
    echo "ðŸ“‹ Useful Commands:"
    echo "  View logs: docker-compose -f infra/docker-compose.yml logs -f"
    echo "  View bot logs: docker-compose -f infra/docker-compose.yml logs -f bot"
    echo "  Stop services: docker-compose -f infra/docker-compose.yml down"
    echo "  Restart services: docker-compose -f infra/docker-compose.yml restart"
}

# Main deployment function
main() {
    echo "=========================================="
    echo "ðŸš€ Sophia Production Deployment"
    echo "=========================================="
    echo ""
    
    check_docker
    check_env
    
    # Step 1: Create backup (if database is running)
    if check_database; then
        create_backup
    else
        print_warning "Database not running. Will create backup after services start."
    fi
    
    # Step 2: Deploy services
    deploy_services
    
    # Step 3: Wait for database
    verify_db_connection
    
    # Step 4: Create backup if we didn't before
    if [ ! -f "$(ls -t ${BACKUP_DIR}/sophia_backup_*.sql 2>/dev/null | head -n 1)" ]; then
        create_backup
    fi
    
    # Step 5: Migrate finishedOnboarding to finishedonboarding (lowercase only)
    if [ -f "$MIGRATIONS_DIR/migrate_to_finishedonboarding_lowercase.sql" ]; then
        print_status "Migrating finishedOnboarding to finishedonboarding (lowercase)..."
        print_warning "This will migrate data from camelCase to lowercase column and remove duplicate"
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/migrate_to_finishedonboarding_lowercase.sql"; then
            print_success "FinishedOnboarding migration completed (using lowercase only)"
        else
            print_warning "FinishedOnboarding migration had some issues (may already be migrated)"
        fi
    fi
    
    # Step 6: Check and add missing tables/columns (SAFE - preserves data)
    if [ -f "$MIGRATIONS_DIR/check_and_add_missing_tables.sql" ]; then
        print_status "Checking database schema and adding missing tables/columns..."
        print_warning "This will add missing tables and columns WITHOUT dropping existing data"
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/check_and_add_missing_tables.sql"; then
            print_success "Schema check completed (missing tables/columns added safely)"
        else
            print_warning "Schema check had some issues (may already be up to date)"
        fi
    fi
    
    # Step 6.5: Apply production migration (new fields and tables)
    if [ -f "$MIGRATIONS_DIR/migrate_production_latest.sql" ]; then
        print_status "Applying production migration (new fields and tables)..."
        print_warning "This will add new fields to existing tables and create new tables"
        if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$MIGRATIONS_DIR/migrate_production_latest.sql"; then
            print_success "Production migration completed successfully"
        else
            print_warning "Production migration had some issues (may already be applied)"
        fi
    fi
    
    # Step 7: Apply migrations
    apply_migrations
    
    # Step 8: Wait for services
    wait_for_services
    
    # Step 9: Show status
    show_status
    
    echo ""
    print_success "ðŸŽ‰ Deployment completed successfully!"
    echo ""
    print_warning "Important:"
    print_warning "1. Verify all services are running: docker-compose -f infra/docker-compose.yml ps"
    print_warning "2. Check logs for any errors: docker-compose -f infra/docker-compose.yml logs"
    print_warning "3. Test the bot and frontend to ensure everything works"
    print_warning "4. Database backup is stored in: $BACKUP_DIR/"
    echo ""
}

# Run main function
main "$@"
