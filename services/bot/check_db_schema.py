"""Check if matches_disabled column exists in users table"""
import asyncio
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5433/postgres")
if "@db:" in DB_URL:
    DB_URL = DB_URL.replace("@db:5432", "@localhost:5433")
elif "@localhost:5432" in DB_URL:
    DB_URL = DB_URL.replace("@localhost:5432", "@localhost:5433")

ANTON_USER_ID = 1541686636

async def check_schema():
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        async with db_pool.acquire() as conn:
            print("=" * 70)
            print("Checking database schema for matches_disabled column")
            print("=" * 70)
            
            # Check if column exists
            column_info = await conn.fetchrow(
                """
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                  AND table_name = 'users' 
                  AND column_name = 'matches_disabled'
                """
            )
            
            if column_info:
                print(f"\nColumn exists:")
                print(f"  Name: {column_info['column_name']}")
                print(f"  Type: {column_info['data_type']}")
                print(f"  Default: {column_info['column_default']}")
                print(f"  Nullable: {column_info['is_nullable']}")
            else:
                print("\n[ERROR] Column 'matches_disabled' does NOT exist in users table!")
                print("  Need to run migration: ALTER TABLE users ADD COLUMN matches_disabled boolean DEFAULT false;")
                return
            
            # Check actual value for Anton
            print("\n" + "=" * 70)
            print("Checking actual value for Anton")
            print("=" * 70)
            
            row = await conn.fetchrow(
                "SELECT user_id, matches_disabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if row:
                print(f"  user_id: {row['user_id']}")
                print(f"  matches_disabled: {row['matches_disabled']}")
                print(f"  Type: {type(row['matches_disabled'])}")
                print(f"  Raw value: {repr(row['matches_disabled'])}")
            else:
                print(f"  [ERROR] User {ANTON_USER_ID} not found!")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
