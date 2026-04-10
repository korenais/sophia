@echo off
REM Database migration deployment script for Windows
REM This script ensures all database migrations are applied correctly
REM Usage: deploy_migrations.bat [DB_URL]

setlocal enabledelayedexpansion

REM Default database URL
if "%1"=="" (
    set DB_URL=postgresql://postgres:postgres@localhost:5432/postgres
) else (
    set DB_URL=%1
)

echo Starting database migration deployment...
echo Database URL: %DB_URL%

REM Check if psql is available
where psql >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: psql command not found. Please install PostgreSQL client tools.
    exit /b 1
)

REM Test database connection
echo Testing database connection...
psql "%DB_URL%" -c "SELECT 1;" >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Cannot connect to database. Please check your connection string.
    exit /b 1
)
echo Database connection successful

REM Run migrations in order
echo Running database migrations...

REM 1. Run the comprehensive migration script
echo Running comprehensive database migration...
psql "%DB_URL%" -f migrate_to_latest.sql
if %errorlevel% neq 0 (
    echo ERROR: Comprehensive database migration failed
    exit /b 1
)
echo Comprehensive database migration completed successfully

REM 2. Run the field_of_activity specific migration (as backup)
echo Running field of activity column migration...
psql "%DB_URL%" -f add_field_of_activity_column.sql
if %errorlevel% neq 0 (
    echo ERROR: Field of activity column migration failed
    exit /b 1
)
echo Field of activity column migration completed successfully

REM 3. Run the user groups migration
echo Running user groups migration...
psql "%DB_URL%" -f add_user_groups.sql
if %errorlevel% neq 0 (
    echo ERROR: User groups migration failed
    exit /b 1
)
echo User groups migration completed successfully

REM 4. Verify the schema
echo Running database schema verification...
psql "%DB_URL%" -f verify_schema.sql
if %errorlevel% neq 0 (
    echo ERROR: Database schema verification failed
    exit /b 1
)
echo Database schema verification completed successfully

echo.
echo Database migration deployment completed successfully!
echo All tables, columns, and indexes are properly set up.
echo.
echo Next steps:
echo 1. Start your application services
echo 2. Test the application functionality
echo 3. Monitor application logs for any issues











