"""Quick script to check created test matches"""
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

async def check():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    async with pool.acquire() as conn:
        # Check Anton
        anton = await conn.fetchrow(
            "SELECT user_id, intro_name, finishedonboarding, state FROM users WHERE user_id = 1541686636"
        )
        print(f"Anton Anisimov: {dict(anton) if anton else 'NOT FOUND'}")
        
        # Check meetings
        meetings = await conn.fetch(
            """
            SELECT id, user_1_id, user_2_id, status, created_at 
            FROM meetings 
            WHERE (user_1_id = 1541686636 OR user_2_id = 1541686636) 
            AND id >= 1330
            ORDER BY id DESC
            LIMIT 5
            """
        )
        print(f"\nMeetings for Anton: {len(meetings)}")
        for m in meetings:
            print(f"  Meeting ID: {m['id']}, Status: {m['status']}, Users: {m['user_1_id']} <-> {m['user_2_id']}")
        
        # Check test users
        test_users = await conn.fetch(
            "SELECT user_id, intro_name, state, finishedonboarding FROM users WHERE user_id IN (9000001, 9000002, 9000003)"
        )
        print(f"\nTest users: {len(test_users)}")
        for u in test_users:
            print(f"  User ID: {u['user_id']}, Name: {u['intro_name']}, State: {u['state']}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(check())
