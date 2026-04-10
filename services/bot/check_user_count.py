"""Check how many users would be processed"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / "infra" / ".env")
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5433/postgres").replace("@db:5432", "@localhost:5433")

async def check():
    pool = await asyncpg.create_pool(DB_URL, command_timeout=5)
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT COUNT(*) 
            FROM users 
            WHERE notifications_enabled=true 
              AND state='ACTIVE' 
              AND finishedonboarding=true
            """
        )
        print(f"Active users with notifications enabled: {count}")
        if count > 10:
            print(f"WARNING: {count} users will be processed - this may take a long time!")
    await pool.close()

asyncio.run(check())
