"""Fix user language to match BOT_LANGUAGE"""
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
ANTON_USER_ID = 1541686636

async def fix_language():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Get current language
            row = await conn.fetchrow(
                "SELECT language, intro_name FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            if row:
                current_lang = row["language"]
                print(f"Current language for {row['intro_name']}: {current_lang}")
                print(f"BOT_LANGUAGE from env: {BOT_LANGUAGE}")
                
                if current_lang != BOT_LANGUAGE:
                    # Update language
                    await conn.execute(
                        "UPDATE users SET language = $1, updated_at = NOW() WHERE user_id = $2",
                        BOT_LANGUAGE,
                        ANTON_USER_ID
                    )
                    print(f"[OK] Updated language from '{current_lang}' to '{BOT_LANGUAGE}'")
                else:
                    print(f"[INFO] Language already set to '{BOT_LANGUAGE}'")
            else:
                print(f"[ERROR] User {ANTON_USER_ID} not found")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(fix_language())
