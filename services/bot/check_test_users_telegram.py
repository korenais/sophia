"""Check if test users have telegram links"""
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

TEST_USER_IDS = [9000001, 9000002, 9000003]

async def check():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            for user_id in TEST_USER_IDS:
                user = await conn.fetchrow(
                    "SELECT user_id, intro_name, user_telegram_link FROM users WHERE user_id = $1",
                    user_id
                )
                if user:
                    print(f"User {user_id} ({user['intro_name']}):")
                    print(f"  user_telegram_link: {user['user_telegram_link']}")
                    if not user['user_telegram_link']:
                        print(f"  [WARNING] No telegram link! Setting test link...")
                        await conn.execute(
                            "UPDATE users SET user_telegram_link = $1 WHERE user_id = $2",
                            f"testuser{user_id}",
                            user_id
                        )
                        print(f"  [OK] Set user_telegram_link to testuser{user_id}")
                else:
                    print(f"User {user_id}: NOT FOUND")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(check())
