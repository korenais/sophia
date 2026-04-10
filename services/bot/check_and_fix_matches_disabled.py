"""Check and fix matches_disabled status for Anton"""
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

async def check_and_fix():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Check current status
            user_row = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state, finishedonboarding FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not user_row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print(f"User: {user_row['intro_name']}")
            print(f"matches_disabled: {user_row['matches_disabled']}")
            print(f"state: {user_row['state']}")
            finished_onboarding = user_row.get('finishedonboarding')
            print(f"finishedOnboarding: {finished_onboarding}")
            
            if user_row['matches_disabled']:
                print("\n[WARNING] Matches are disabled! Enabling them...")
                await conn.execute(
                    "UPDATE users SET matches_disabled = false, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] Matches enabled!")
            else:
                print("\n[OK] Matches are enabled")
            
            # Also ensure user is ACTIVE and finished onboarding
            if user_row['state'] != 'ACTIVE':
                print(f"\n[WARNING] User state is '{user_row['state']}', setting to ACTIVE...")
                await conn.execute(
                    "UPDATE users SET state = 'ACTIVE', updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] State set to ACTIVE")
            
            if not finished_onboarding:
                print("\n[WARNING] User hasn't finished onboarding, setting finishedonboarding = true...")
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] finishedonboarding set to true")
            
            # Verify
            updated_row = await conn.fetchrow(
                "SELECT matches_disabled, state, finishedonboarding FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print("\n[FINAL STATUS]")
            print(f"matches_disabled: {updated_row['matches_disabled']}")
            print(f"state: {updated_row['state']}")
            print(f"finishedonboarding: {updated_row['finishedonboarding']}")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(check_and_fix())
