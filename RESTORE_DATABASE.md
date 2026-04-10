# Database Restore Guide

## How to Restore from Database Dump

This guide explains how to restore the database from a dump file created by `dump_database.sh` or `dump_database.bat`.

## Prerequisites

1. Database dump file (`.sql` or `.sql.gz`)
2. Database container running (or PostgreSQL server)
3. Access to Docker (if using containers)

## Restore Methods

### Method 1: Restore to Docker Container (Recommended)

#### For uncompressed SQL file:

**Linux/macOS:**
```bash
# Find database container
docker ps | grep postgres

# Restore
docker exec -i <container-name> psql -U postgres < backups/sophia_dump_2024-01-01_12-00-00.sql
```

**Windows:**
```cmd
type backups\sophia_dump_2024-01-01_12-00-00.sql | docker exec -i <container-name> psql -U postgres
```

#### For compressed SQL file (.gz):

**Linux/macOS:**
```bash
# Method 1: Pipe directly (recommended)
gunzip < backups/sophia_dump_2024-01-01_12-00-00.sql.gz | docker exec -i <container-name> psql -U postgres

# Method 2: Extract first, then restore
gunzip backups/sophia_dump_2024-01-01_12-00-00.sql.gz
docker exec -i <container-name> psql -U postgres < backups/sophia_dump_2024-01-01_12-00-00.sql
```

**Windows:**
```cmd
REM Extract first (requires 7-Zip or similar)
REM Then restore using Method 1 above
```

### Method 2: Restore to Local PostgreSQL Server

If you have PostgreSQL installed locally (not in Docker):

**Linux/macOS:**
```bash
# Uncompressed
psql -h localhost -U postgres -d postgres < backups/sophia_dump_2024-01-01_12-00-00.sql

# Compressed
gunzip < backups/sophia_dump_2024-01-01_12-00-00.sql.gz | psql -h localhost -U postgres -d postgres
```

**Windows:**
```cmd
psql -h localhost -U postgres -d postgres < backups\sophia_dump_2024-01-01_12-00-00.sql
```

### Method 3: Restore to Remote PostgreSQL Server

```bash
# Uncompressed
psql -h your-server.com -U postgres -d postgres < backups/sophia_dump_2024-01-01_12-00-00.sql

# Compressed
gunzip < backups/sophia_dump_2024-01-01_12-00-00.sql.gz | psql -h your-server.com -U postgres -d postgres
```

## Step-by-Step Restore Process

### 1. Stop Services (Recommended)

To avoid conflicts during restore:

```bash
cd infra
docker-compose stop bot api frontend
# Keep database running
```

### 2. Backup Current Database (Important!)

Before restoring, create a backup of the current state:

```bash
./dump_database.sh backups/before_restore_backup.sql
```

### 3. Restore the Dump

Choose one of the methods above based on your setup.

### 4. Verify Restore

Check that data was restored correctly:

```bash
# Connect to database
docker exec -it <container-name> psql -U postgres -d postgres

# Check table counts
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM meetings;
SELECT COUNT(*) FROM feedbacks;
SELECT COUNT(*) FROM thanks;

# Exit
\q
```

### 5. Restart Services

```bash
cd infra
docker-compose up -d
```

## Important Notes

### ⚠️ Warning: DROP Statements

The dump file includes `DROP` statements (`--clean --if-exists` flags). This means:
- Existing tables will be dropped before restoring
- **All current data will be lost** if you restore over an existing database
- Always create a backup before restoring

### Database Creation

The dump includes `CREATE DATABASE` statements (`--create` flag). When restoring:
- If restoring to an existing database, you may need to connect to `postgres` database first
- The dump will create the database if it doesn't exist

### Owner and Privileges

The dump uses `--no-owner --no-privileges` flags, which means:
- Objects will be owned by the user running the restore
- Default privileges will be applied
- This ensures compatibility across different PostgreSQL setups

## Troubleshooting

### Error: "database does not exist"

If you get this error, connect to the `postgres` database first:

```bash
docker exec -i <container-name> psql -U postgres -d postgres < dump_file.sql
```

The dump includes `CREATE DATABASE` statements, so it should work.

### Error: "permission denied"

Make sure you're using the correct user:
- Default: `postgres`
- Or check your `infra/.env` file for `POSTGRES_USER`

### Error: "relation already exists"

This shouldn't happen with `--clean --if-exists`, but if it does:
1. Drop the database manually: `DROP DATABASE postgres;`
2. Create it again: `CREATE DATABASE postgres;`
3. Restore again

### Restore is slow

Large databases take time to restore. Be patient. You can monitor progress by:
- Checking database logs: `docker-compose -f infra/docker-compose.yml logs db`
- Checking disk I/O: `docker stats`

## Quick Restore Command Reference

**Most common restore command (Docker, uncompressed):**
```bash
docker exec -i $(docker ps --format "{{.Names}}" | grep -E "(db|postgres)") psql -U postgres < backups/sophia_dump_YYYY-MM-DD_HH-MM-SS.sql
```

**Most common restore command (Docker, compressed):**
```bash
gunzip < backups/sophia_dump_YYYY-MM-DD_HH-MM-SS.sql.gz | docker exec -i $(docker ps --format "{{.Names}}" | grep -E "(db|postgres)") psql -U postgres
```

## Examples

### Example 1: Restore Latest Dump

```bash
# Find latest dump file
LATEST_DUMP=$(ls -t backups/sophia_dump_*.sql* | head -n 1)
echo "Restoring: $LATEST_DUMP"

# Restore
if [[ "$LATEST_DUMP" == *.gz ]]; then
    gunzip < "$LATEST_DUMP" | docker exec -i $(docker ps --format "{{.Names}}" | grep postgres | head -n 1) psql -U postgres
else
    docker exec -i $(docker ps --format "{{.Names}}" | grep postgres | head -n 1) psql -U postgres < "$LATEST_DUMP"
fi
```

### Example 2: Restore with Verification

```bash
# Backup current state
./dump_database.sh backups/before_restore_$(date +%Y%m%d_%H%M%S).sql

# Restore
docker exec -i <container-name> psql -U postgres < backups/sophia_dump_2024-01-01_12-00-00.sql

# Verify
docker exec -it <container-name> psql -U postgres -d postgres -c "SELECT COUNT(*) FROM users;"
```

---

**Remember:** Always backup before restoring! The restore process will delete existing data.
