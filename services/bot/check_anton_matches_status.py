"""Check matches_disabled status for Anton Anisimov"""
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

async def check_status():
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        async with db_pool.acquire() as conn:
            print("=" * 70)
            print("Checking matches_disabled status for Anton Anisimov")
            print("=" * 70)
            
            user_row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, matches_disabled, state, finishedonboarding, 
                       notifications_enabled, updated_at
                FROM users 
                WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            
            if not user_row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print(f"\nUser Information:")
            print(f"  Name: {user_row['intro_name']}")
            print(f"  User ID: {user_row['user_id']}")
            print(f"\nMatch Settings:")
            print(f"  matches_disabled: {user_row['matches_disabled']}")
            if user_row['matches_disabled']:
                print(f"  Status: [DISABLED] RECOMMENDATIONS DISABLED")
                print(f"  Meaning: User will NOT receive new match recommendations")
            else:
                print(f"  Status: [ENABLED] RECOMMENDATIONS ENABLED")
                print(f"  Meaning: User WILL receive new match recommendations")
            print(f"\nOther Settings:")
            print(f"  state: {user_row['state']}")
            print(f"  finishedonboarding: {user_row['finishedonboarding']}")
            print(f"  notifications_enabled: {user_row['notifications_enabled']}")
            print(f"  Last updated: {user_row['updated_at']}")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(check_status())

