# Database Migrations

This directory contains all database migration scripts for the Sophia application.

## Migration Files

### Core Migration Scripts

1. **`init.sql`** - Initial database schema creation
   - Creates all tables and indexes from scratch
   - Used for fresh database installations

2. **`migrate_to_latest.sql`** - Comprehensive migration script
   - Updates existing databases to the latest schema
   - Safe to run multiple times (idempotent)
   - Includes all column additions and updates

3. **`add_field_of_activity_column.sql`** - Specific migration for field_of_activity
   - Adds the field_of_activity column to users table
   - Sets default values for existing users
   - Can be run independently if needed

### Verification Scripts

4. **`verify_schema.sql`** - Database schema verification
   - Checks that all required tables and columns exist
   - Verifies indexes are present
   - Validates field_of_activity column specifically

### Deployment Scripts

5. **`deploy_migrations.sh`** - Linux/macOS deployment script
   - Runs all migrations in correct order
   - Includes error handling and verification
   - Usage: `./deploy_migrations.sh [DB_URL]`

6. **`deploy_migrations.bat`** - Windows deployment script
   - Same functionality as shell script
   - Usage: `deploy_migrations.bat [DB_URL]`

## Production Deployment

### Prerequisites

1. PostgreSQL client tools installed (`psql` command available)
2. Database connection string
3. Appropriate database permissions

### Deployment Steps

#### Option 1: Using Deployment Scripts (Recommended)

**Linux/macOS:**
```bash
cd services/db
chmod +x deploy_migrations.sh
./deploy_migrations.sh "postgresql://user:password@host:port/database"
```

**Windows:**
```cmd
cd services\db
deploy_migrations.bat "postgresql://user:password@host:port/database"
```

#### Option 2: Manual Migration

```bash
# 1. Run comprehensive migration
psql "postgresql://user:password@host:port/database" -f migrate_to_latest.sql

# 2. Run field_of_activity specific migration (backup)
psql "postgresql://user:password@host:port/database" -f add_field_of_activity_column.sql

# 3. Verify schema
psql "postgresql://user:password@host:port/database" -f verify_schema.sql
```

### Docker Deployment

If using Docker, you can run migrations inside the container:

```bash
# Copy migration files to container
docker cp services/db/migrate_to_latest.sql container_name:/tmp/
docker cp services/db/add_field_of_activity_column.sql container_name:/tmp/
docker cp services/db/verify_schema.sql container_name:/tmp/

# Run migrations
docker exec container_name psql -U postgres -d postgres -f /tmp/migrate_to_latest.sql
docker exec container_name psql -U postgres -d postgres -f /tmp/add_field_of_activity_column.sql
docker exec container_name psql -U postgres -d postgres -f /tmp/verify_schema.sql
```

## Migration Details

### field_of_activity Column

The `field_of_activity` column was added to the `users` table with the following specifications:

- **Type**: `TEXT`
- **Nullable**: `YES`
- **Default**: `'Not specified'` for existing users
- **Comment**: `'Field of activity/profession of the user'`

### Backward Compatibility

All migrations are designed to be backward compatible:
- Uses `IF NOT EXISTS` clauses to prevent errors on re-runs
- Preserves existing data
- Sets appropriate default values for new columns

### Error Handling

The migration scripts include comprehensive error handling:
- Verification steps after each major change
- Clear error messages if something fails
- Rollback-safe operations

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure the database user has `ALTER TABLE` permissions
   - Check that the user can create indexes

2. **Connection Issues**
   - Verify the database URL is correct
   - Check network connectivity
   - Ensure PostgreSQL is running

3. **Column Already Exists**
   - This is normal and expected
   - The scripts use `IF NOT EXISTS` to handle this gracefully

### Verification

After running migrations, verify the setup:

```sql
-- Check if field_of_activity column exists
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'field_of_activity';

-- Check if any users have NULL values
SELECT COUNT(*) FROM users WHERE field_of_activity IS NULL;

-- Check total users
SELECT COUNT(*) FROM users;
```

## Support

If you encounter issues during migration:

1. Check the database logs for detailed error messages
2. Verify your database connection string
3. Ensure you have the necessary permissions
4. Run the verification script to identify specific issues

The migration scripts are designed to be safe and can be run multiple times without issues.











