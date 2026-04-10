"""
Script to apply user groups migration to database
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Get DB_URL
default_db_url = "postgresql://postgres:postgres@localhost:5433/postgres"
DB_URL = os.getenv("DB_URL", default_db_url)
if DB_URL:
    if "@db:" in DB_URL:
        DB_URL = DB_URL.replace("@db:5432", "@localhost:5433")
    elif "@localhost:5432" in DB_URL:
        DB_URL = DB_URL.replace("@localhost:5432", "@localhost:5433")

async def apply_migration():
    """Apply user groups migration"""
    migration_file = Path(__file__).parent.parent / "db" / "add_user_groups.sql"
    
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return False
    
    print(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    print(f"Connecting to database: {DB_URL[:50]}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected successfully")
        
        print("Applying migration...")
        await conn.execute(migration_sql)
        print("Migration applied successfully")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"ERROR: Failed to apply migration: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)

