# 🚀 Sophia Bot - Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Sophia bot to production with proper database backup and migration procedures.

## ⚠️ Important: Database Safety

**Every deployment starts with a database backup** to ensure data safety. The deployment scripts automatically:
1. Create a database backup before any changes
2. Apply migrations safely (adds missing fields, never drops data)
3. Verify the database schema after migrations
4. Keep the last 10 backups for recovery

## 📦 Deployment Package Contents

The `deploy.zip` file contains:

```
deploy.zip
├── infra/                          # Docker Compose configuration
│   ├── docker-compose.yml         # Main orchestration file
│   └── env.sample.txt              # Environment variables template
├── services/                       # Application services
│   ├── api/                        # FastAPI backend
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── bot/                        # Telegram bot
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── scenes.py
│   │   └── requirements.txt
│   ├── db/                         # Database migrations
│   │   ├── init.sql                # Initial schema
│   │   ├── migrate_to_latest.sql  # Comprehensive migration
│   │   ├── add_field_of_activity_column.sql
│   │   ├── verify_schema.sql       # Schema verification
│   │   ├── deploy_migrations.sh    # Migration script (Linux)
│   │   └── deploy_migrations.bat   # Migration script (Windows)
│   └── frontend/                   # React admin panel
│       ├── Dockerfile
│       ├── package.json
│       └── src/
├── systemd/                        # System service configuration (optional)
│   ├── sophia-fixed.service
│   └── setup_sophia_service.sh
├── backups/                        # Database backups (created during deployment)
├── deploy_production.sh            # Main deployment script (Linux/macOS)
├── deploy_production.bat            # Main deployment script (Windows)
├── backup_database_production.sh   # Standalone backup script
├── production.env.example           # Production environment template
└── DEPLOYMENT_PRODUCTION.md         # This file
```

## 🛠️ Prerequisites

**For Linux Production Server:**

1. **Docker and Docker Compose** installed and running
   ```bash
   # Check Docker
   docker --version
   docker-compose --version
   
   # If not installed, install Docker:
   # Ubuntu/Debian:
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose:
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **PostgreSQL client tools** (usually included with Docker, but can install separately if needed)
3. **SSH access** to production server with appropriate permissions
4. **Environment variables** configured (see Configuration section)
5. **Sufficient resources**: At least 2GB RAM, 10GB disk space

## 📋 Deployment Steps

### Step 1: Extract Deployment Package

```bash
# Extract the archive
unzip deploy.zip
cd deploy

# Or if already extracted, navigate to the directory
cd /path/to/sophia
```

### Step 2: Configure Environment

1. **Copy environment template:**
   ```bash
   cp infra/env.sample.txt infra/.env
   ```

2. **Edit `infra/.env`** with your production values:
   ```bash
   # Required settings
   TELEGRAM_TOKEN=your_bot_token_here
   OPENAI_API_KEY=your_openai_key_here
   GEOCODING_API_KEY=your_geocoding_key_here
   
   # Database settings (if using custom values)
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=secure_password_here
   POSTGRES_DB=postgres
   
   # Frontend settings
   FRONTEND_PASSWD=secure_admin_password_here
   VITE_API_BASE_URL=https://your-domain.com:8055
   
   # Bot settings
   BOT_LANGUAGE=ru  # or 'en'
   BIRTHDAYS=No  # or 'Yes' to enable birthday greetings
   
   # Optional: Group and topic settings
   TELEGRAM_GROUP_ID=-1001234567890
   THANKS_TOPIC_ID=4
   BIRTHDAY_TOPIC_ID=7
   ```

### Step 3: Fix Line Endings (if needed)

**Important:** If you extracted the package on Windows or transferred from Windows, you may need to fix line endings:

```bash
# Option 1: Using dos2unix (install first: sudo apt-get install dos2unix)
dos2unix deploy_production.sh backup_database_production.sh dump_database.sh
dos2unix services/db/*.sh

# Option 2: Using sed (no installation needed)
sed -i 's/\r$//' deploy_production.sh backup_database_production.sh dump_database.sh
find services/db -name "*.sh" -exec sed -i 's/\r$//' {} \;

# Make scripts executable
chmod +x deploy_production.sh backup_database_production.sh dump_database.sh
chmod +x services/db/*.sh
```

If you see `bad interpreter: No such file or directory` error, see `FIX_LINE_ENDINGS.md` for details.

### Step 4: Run Deployment Script

**On Linux Production Server:**
```bash
# Run deployment (this will automatically):
# - Create database backup
# - Deploy services
# - Apply migrations safely
# - Verify everything is working
./deploy_production.sh
```

**Note:** The deployment script is optimized for Linux. It will automatically handle all deployment steps including database backup and migrations.

### What the Deployment Script Does

The deployment script automatically:

1. ✅ **Checks Docker** - Verifies Docker and Docker Compose are installed and running
2. ✅ **Checks Environment** - Verifies `.env` file exists and is configured
3. ✅ **Creates Database Backup** - Creates a timestamped backup before any changes
4. ✅ **Deploys Services** - Builds and starts all Docker containers
5. ✅ **Waits for Database** - Ensures database is ready before migrations
6. ✅ **Applies Migrations** - Safely adds missing fields and functions
7. ✅ **Verifies Schema** - Confirms all required tables and columns exist
8. ✅ **Waits for Services** - Ensures all services are running
9. ✅ **Shows Status** - Displays service status and access URLs

## 🔄 Database Migrations

### ⚠️ Important: Migrations Do NOT Run Automatically

**Important Note:** Database migrations do **NOT** run automatically during `docker-compose build` or `docker-compose up`.

- `docker-compose build` - Only builds Docker images, does not run migrations
- `docker-compose up` - Starts containers, but migration scripts in `/docker-entrypoint-initdb.d/` only run on **first database initialization** (when database is empty)

**For production deployments with existing databases**, migrations must be run manually, which is what `deploy_production.sh` does automatically.

### Automatic Migrations via Deployment Script

The `deploy_production.sh` script automatically applies migrations after services start. The migration process:

- ✅ **Safe** - Uses `IF NOT EXISTS` clauses to prevent errors
- ✅ **Non-destructive** - Only adds missing fields, never drops data
- ✅ **Idempotent** - Can be run multiple times safely
- ✅ **Verified** - Schema verification confirms success

### Migration Scripts

1. **`migrate_to_latest.sql`** - Comprehensive migration that adds:
   - `user_telegram_link` column
   - `language` column with default 'en'
   - `sent_followup_message` column in meetings
   - `field_of_activity` column
   - All necessary indexes

2. **`add_field_of_activity_column.sql`** - Backup migration for field_of_activity

3. **`verify_schema.sql`** - Verifies all tables, columns, and indexes exist

### Manual Migration (if needed)

**Note:** The `deploy_production.sh` script handles migrations automatically. Only use manual migration if you need to run migrations separately.

**Using Docker (Recommended for production):**
```bash
# After services are running, find the database container name
docker ps | grep postgres

# Run migrations via docker exec
docker exec -i <db-container-name> psql -U postgres -d postgres < services/db/migrate_to_latest.sql
docker exec -i <db-container-name> psql -U postgres -d postgres < services/db/add_field_of_activity_column.sql
docker exec -i <db-container-name> psql -U postgres -d postgres < services/db/verify_schema.sql
```

**Using psql directly (requires PostgreSQL client):**
```bash
cd services/db
chmod +x deploy_migrations.sh
./deploy_migrations.sh "postgresql://user:password@host:port/database"
```

**See `MIGRATION_NOTES.md` for detailed information about when migrations run.**

## 💾 Database Backups

### Automatic Backups

Every deployment automatically creates a backup in the `backups/` directory:
- Format: `sophia_backup_YYYY-MM-DD_HH-MM-SS.sql`
- Location: `backups/` directory
- Retention: Last 10 backups are kept

### Manual Backup

To create a backup manually:

**Linux/macOS:**
```bash
chmod +x backup_database_production.sh
./backup_database_production.sh
```

**Windows:**
```cmd
# Using Docker directly
docker exec sophia-db-1 pg_dump -U postgres -d postgres > backups\backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
```

### Restore from Backup

**Linux/macOS:**
```bash
# If backup is compressed
gunzip < backups/sophia_backup_2024-01-01_12-00-00.sql.gz | docker exec -i sophia-db-1 psql -U postgres -d postgres

# If backup is not compressed
docker exec -i sophia-db-1 psql -U postgres -d postgres < backups/sophia_backup_2024-01-01_12-00-00.sql
```

**Windows:**
```cmd
type backups\sophia_backup_2024-01-01_12-00-00.sql | docker exec -i sophia-db-1 psql -U postgres -d postgres
```

## 🔍 Verification

After deployment, verify everything is working:

### 1. Check Service Status

```bash
cd infra
docker-compose ps
```

All services should show "Up" status.

### 2. Check Logs

```bash
# All services
docker-compose -f infra/docker-compose.yml logs

# Specific service
docker-compose -f infra/docker-compose.yml logs bot
docker-compose -f infra/docker-compose.yml logs api
docker-compose -f infra/docker-compose.yml logs frontend
```

### 3. Test Endpoints

```bash
# API health check
curl http://localhost:8055/api/health

# Frontend (should show login page)
curl http://localhost:8081
```

### 4. Test Bot

1. Open Telegram
2. Find your bot
3. Send `/start` command
4. Verify bot responds correctly

### 5. Test Frontend

1. Open browser: `http://localhost:8081`
2. Login with configured password
3. Verify dashboard loads
4. Check users, matches, and other tabs

## 🐛 Troubleshooting

### Database Connection Issues

**Problem:** Database container not found
**Solution:** 
```bash
cd infra
docker-compose up -d db
# Wait for database to start, then retry deployment
```

### Migration Failures

**Problem:** Migration script fails
**Solution:**
1. Check database logs: `docker-compose -f infra/docker-compose.yml logs db`
2. Verify database credentials in `infra/.env`
3. Run migrations manually (see Manual Migration section)

### Service Won't Start

**Problem:** Services fail to start
**Solution:**
1. Check logs: `docker-compose -f infra/docker-compose.yml logs`
2. Verify environment variables in `infra/.env`
3. Check port conflicts: `netstat -an | grep 8055` (or `8081`)
4. Restart Docker: `sudo systemctl restart docker` (Linux) or restart Docker Desktop (Windows)

### Backup Issues

**Problem:** Backup file is empty
**Solution:**
1. Verify database container is running: `docker ps | grep db`
2. Check database credentials
3. Verify database name matches configuration
4. Try manual backup (see Manual Backup section)

## 📊 Monitoring

### View Real-time Logs

```bash
# All services
docker-compose -f infra/docker-compose.yml logs -f

# Specific service
docker-compose -f infra/docker-compose.yml logs -f bot
```

### Service Status

```bash
docker-compose -f infra/docker-compose.yml ps
```

### Resource Usage

```bash
docker stats
```

## 🔄 Updating Deployment

To update an existing deployment:

1. **Create backup** (automatic in deployment script)
2. **Stop services:**
   ```bash
   cd infra
   docker-compose down
   ```
3. **Update code** (extract new deploy.zip or pull updates)
4. **Run deployment script** again:
   ```bash
   ./deploy_production.sh
   ```

The script will:
- Create a new backup
- Apply any new migrations
- Rebuild and restart services

## 🔒 Security Best Practices

1. **Change Default Passwords** - Update `FRONTEND_PASSWD` and `POSTGRES_PASSWORD`
2. **Use HTTPS** - Configure reverse proxy with SSL certificates
3. **Firewall Rules** - Only expose necessary ports
4. **Regular Backups** - Schedule automated backups
5. **Monitor Logs** - Check logs regularly for issues
6. **Update Regularly** - Keep Docker and dependencies updated

## 📞 Support

For issues:
1. Check logs: `docker-compose -f infra/docker-compose.yml logs`
2. Verify environment: `cat infra/.env`
3. Check service status: `docker-compose -f infra/docker-compose.yml ps`
4. Review this documentation

## 📝 Deployment Checklist

- [ ] Docker and Docker Compose installed
- [ ] Environment file configured (`infra/.env`)
- [ ] Database backup created (automatic)
- [ ] Services deployed successfully
- [ ] Migrations applied
- [ ] Schema verified
- [ ] All services running
- [ ] Bot responding to commands
- [ ] Frontend accessible
- [ ] API health check passing
- [ ] Logs checked for errors

## 📱 TMA Side-by-Side Rollout

Use this path when you want to deploy Telegram Mini App safely without restarting the old bot or replacing the old API behavior.

### Principles

- Keep the existing `infra_bot_1`, `infra_api_1`, `infra_frontend_1`, and `infra_db_1`
- Use the same production database
- Add only additive DB columns for TMA
- Run TMA through a compose override, not through a full in-place redeploy

### Required Production Env

Add these lines to `infra/.env`:

```env
TMA_URL=https://vm18.digisoov.ee/tma/
TMA_VITE_API_BASE_URL=/tma-api
TMA_VITE_APP_BASE_PATH=/tma/
TMA_CORS_ALLOWED_ORIGINS=https://vm18.digisoov.ee
TMA_ALLOWED_USER_IDS=6461565453,423138096
```

Notes:
- `TMA_ALLOWED_USER_IDS` is optional but recommended for private rollout
- it limits Mini App access without affecting the old bot
- current test users are `6461565453` and `423138096`

### Files Required

- `infra/docker-compose.tma.yml`
- `services/tma/*`
- updated `services/api/main.py`
- updated `services/frontend/nginx.conf`
- `services/db/add_tma_columns.sql`

### Deployment Steps

1. Create a fresh DB backup:

```bash
cd /home/aanisimov/sophia
bash ./backup_database_production.sh
```

2. Apply additive TMA migration:

```bash
cd /home/aanisimov/sophia
docker exec -i infra_db_1 psql -U postgres -d postgres < services/db/add_tma_columns.sql
```

3. Start the rollout services:

```bash
cd /home/aanisimov/sophia/infra
docker-compose -f docker-compose.yml -f docker-compose.tma.yml up --build -d frontend api-tma tma
```

What this does:
- rebuilds `frontend` so it proxies `/tma` and `/tma-api`
- starts `api-tma` as a separate API container using the same DB
- starts `tma` as the Mini App frontend
- does not restart the bot

### Production Server Reality

On the current production server (`vm18.digisoov.ee`), `docker-compose` v1 has a known recreate bug:

- error: `KeyError: 'ContainerConfig'`
- it can appear when recreating existing services such as `db` or `frontend`

Because of that, the safest practical rollout path is:

1. Start only new sidecars with `--no-deps`
2. Recreate `frontend` separately, also with `--no-deps`
3. If `frontend` recreate fails with the same bug, remove the old container and create it again

### Recommended Real-World Commands

Start TMA sidecars only:

```bash
cd /home/aanisimov/sophia/infra
docker-compose -f docker-compose.yml -f docker-compose.tma.yml up --build -d --no-deps api-tma tma
```

Recreate frontend ingress safely:

```bash
cd /home/aanisimov/sophia/infra
docker-compose -f docker-compose.yml -f docker-compose.tma.yml up --build -d --no-deps frontend
```

If frontend hits `ContainerConfig`, recover with:

```bash
docker rm -f infra_frontend_1
cd /home/aanisimov/sophia/infra
docker-compose -f docker-compose.yml -f docker-compose.tma.yml up --build -d --no-deps frontend
```

### TMA Routing Fix

The frontend nginx config must use `^~` for TMA routes, otherwise `/tma/assets/*.js` and `/tma/assets/*.css` may be intercepted by the generic static-assets rule and return `404`.

Required locations in `services/frontend/nginx.conf`:

```nginx
location ^~ /tma-api/ {
    proxy_pass http://api-tma:8055/;
}

location ^~ /tma/ {
    proxy_pass http://tma/;
}
```

Without this, Telegram may show a blank white window because the HTML loads but the JS/CSS bundles fail.

### Verification

```bash
curl https://vm18.digisoov.ee/tma/
curl https://vm18.digisoov.ee/tma-api/health
curl -I https://vm18.digisoov.ee/tma/assets/index-*.js
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected:
- `/tma/` returns `200`
- `/tma-api/health` returns healthy JSON
- `/tma/assets/...` returns `200`, not `404`

### Access Control

During private rollout, keep TMA limited to explicit Telegram users:

```env
TMA_ALLOWED_USER_IDS=6461565453,423138096
```

This restriction is enforced in `services/api/main.py` and applies only to TMA endpoints.
The old bot behavior is unchanged.

### Recovery If DB Gets Stopped

If compose v1 touches the DB and the old container stops, but the named volume is still present:

1. Check that `infra_db_data` still exists
2. Start the stopped DB container again
3. Verify with `pg_isready`

Example:

```bash
docker volume ls
docker start <stopped-db-container>
docker exec <stopped-db-container> pg_isready -U postgres -d postgres
```

This restores the old production state without restoring from backup, because the data lives in the Docker volume.

### Rollback

```bash
cd /home/aanisimov/sophia/infra
docker-compose -f docker-compose.yml -f docker-compose.tma.yml stop api-tma tma
docker-compose -f docker-compose.yml -f docker-compose.tma.yml rm -f api-tma tma
docker-compose -f docker-compose.yml up --build -d frontend
```

Rollback impact:
- old bot keeps running
- old API keeps running
- old database stays in place
- only TMA entrypoints disappear

---

**Last Updated:** $(date)
**Version:** Latest with production deployment support
