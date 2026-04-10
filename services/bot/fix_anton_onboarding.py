"""Fix Anton's onboarding status"""
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

async def fix():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Check current status
            user = await conn.fetchrow(
                "SELECT user_id, intro_name, finishedonboarding, state, matches_disabled, vector_description FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not user:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print("=" * 70)
            print(f"Current Status for: {user['intro_name']}")
            print("=" * 70)
            print(f"finishedonboarding: {user['finishedonboarding']}")
            print(f"state: {user['state']}")
            print(f"matches_disabled: {user['matches_disabled']}")
            print(f"vector_description: {'SET' if user['vector_description'] else 'NOT SET'}")
            
            # Fix all issues
            print("\n" + "=" * 70)
            print("Fixing issues...")
            print("=" * 70)
            
            updates = []
            if not user['finishedonboarding']:
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                updates.append("Set finishedonboarding = true")
            
            if user['state'] != 'ACTIVE':
                await conn.execute(
                    "UPDATE users SET state = 'ACTIVE', updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                updates.append(f"Set state = 'ACTIVE' (was {user['state']})")
            
            if user['matches_disabled']:
                await conn.execute(
                    "UPDATE users SET matches_disabled = false, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                updates.append("Set matches_disabled = false")
            
            if updates:
                print(f"[OK] Applied updates: {', '.join(updates)}")
            else:
                print("[OK] No updates needed")
            
            # Verify user is in matchable users
            print("\n" + "=" * 70)
            print("Verifying user is matchable...")
            print("=" * 70)
            
            matchable = await conn.fetchrow(
                """
                SELECT user_id, vector_description, vector_location
                FROM public.users
                WHERE finishedonboarding = true 
                  AND state = 'ACTIVE' 
                  AND vector_description IS NOT NULL
                  AND (matches_disabled IS NULL OR matches_disabled = false)
                  AND user_id = $1
                """,
                ANTON_USER_ID
            )
            
            if matchable:
                print("[OK] User is in matchable users list!")
            else:
                print("[WARNING] User is NOT in matchable users list!")
                print("Checking why...")
                
                # Check each condition
                checks = await conn.fetchrow(
                    "SELECT finishedonboarding, state, vector_description IS NOT NULL as has_vector, matches_disabled FROM users WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print(f"  finishedonboarding: {checks['finishedonboarding']}")
                print(f"  state: {checks['state']}")
                print(f"  has vector_description: {checks['has_vector']}")
                print(f"  matches_disabled: {checks['matches_disabled']}")
            
            # Final status
            print("\n" + "=" * 70)
            print("Final Status:")
            print("=" * 70)
            final = await conn.fetchrow(
                "SELECT finishedonboarding, state, matches_disabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print(f"finishedonboarding: {final['finishedonboarding']}")
            print(f"state: {final['state']}")
            print(f"matches_disabled: {final['matches_disabled']}")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(fix())
