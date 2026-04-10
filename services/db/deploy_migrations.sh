#!/bin/bash

# Database migration deployment script
# This script ensures all database migrations are applied correctly
# Usage: ./deploy_migrations.sh [DB_URL]

set -e  # Exit on any error

# Default database URL
DB_URL=${1:-"postgresql://postgres:postgres@localhost:5432/postgres"}

echo "Starting database migration deployment..."
echo "Database URL: $DB_URL"

# Function to run SQL file
run_sql_file() {
    local file=$1
    local description=$2
    
    echo "Running $description..."
    if psql "$DB_URL" -f "$file"; then
        echo "âœ… $description completed successfully"
    else
        echo "âŒ $description failed"
        exit 1
    fi
}

# Function to run SQL command
run_sql_command() {
    local command=$1
    local description=$2
    
    echo "Running $description..."
    if psql "$DB_URL" -c "$command"; then
        echo "âœ… $description completed successfully"
    else
        echo "âŒ $description failed"
        exit 1
    fi
}

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "âŒ psql command not found. Please install PostgreSQL client tools."
    exit 1
fi

# Test database connection
echo "Testing database connection..."
if ! psql "$DB_URL" -c "SELECT 1;" &> /dev/null; then
    echo "âŒ Cannot connect to database. Please check your connection string."
    exit 1
fi
echo "âœ… Database connection successful"

# Run migrations in order
echo "Running database migrations..."

# 1. Run the comprehensive migration script
run_sql_file "migrate_to_latest.sql" "Comprehensive database migration"

# 2. Run the field_of_activity specific migration (as backup)
run_sql_file "add_field_of_activity_column.sql" "Field of activity column migration"

# 3. Run the user groups migration
run_sql_file "add_user_groups.sql" "User groups migration"

# 4. Verify the schema
run_sql_file "verify_schema.sql" "Database schema verification"

echo ""
echo "ðŸŽ‰ Database migration deployment completed successfully!"
echo "All tables, columns, and indexes are properly set up."
echo ""
echo "Next steps:"
echo "1. Start your application services"
echo "2. Test the application functionality"
echo "3. Monitor application logs for any issues"











