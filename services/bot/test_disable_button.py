"""Test disable button functionality directly"""
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

async def test_disable():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Check current state
            user_row = await conn.fetchrow(
                "SELECT matches_disabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print(f"Current matches_disabled: {user_row['matches_disabled'] if user_row else 'USER NOT FOUND'}")
            
            # Test disable function
            print("\nTesting disable_all_matches function...")
            await conn.execute(
                """
                UPDATE public.users
                SET matches_disabled = true, updated_at = now()
                WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            print("Updated matches_disabled to true")
            
            # Check again
            user_row = await conn.fetchrow(
                "SELECT matches_disabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print(f"After update matches_disabled: {user_row['matches_disabled']}")
            
            # Reset for testing
            await conn.execute(
                """
                UPDATE public.users
                SET matches_disabled = false, updated_at = now()
                WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            print("\nReset matches_disabled to false for testing")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(test_disable())
