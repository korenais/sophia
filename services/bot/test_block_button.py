"""Test block button functionality"""
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
TEST_USER_IDS = [9000001, 9000002, 9000003]

async def test_block():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Check if block exists
            for test_user_id in TEST_USER_IDS:
                block = await conn.fetchrow(
                    "SELECT * FROM match_blocks WHERE user_id = $1 AND blocked_user_id = $2",
                    ANTON_USER_ID,
                    test_user_id
                )
                print(f"Block for user {test_user_id}: {dict(block) if block else 'NOT FOUND'}")
                
                # Check meeting status
                meeting = await conn.fetchrow(
                    """
                    SELECT id, status FROM meetings
                    WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
                if meeting:
                    print(f"Meeting for user {test_user_id}: ID={meeting['id']}, Status={meeting['status']}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(test_block())
