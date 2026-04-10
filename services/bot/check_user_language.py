"""Check user language in database"""
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

BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "ru")

async def check():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, language, intro_name FROM users WHERE user_id = 1541686636"
        )
        print(f"User in DB: {dict(row) if row else None}")
        print(f"BOT_LANGUAGE from env: {BOT_LANGUAGE}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(check())
