"""Debug script to test block button callback data format"""
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

async def debug_callback_data():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            for test_user_id in TEST_USER_IDS:
                # Get meeting
                meeting = await conn.fetchrow(
                    """
                    SELECT id FROM meetings
                    WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
                
                if meeting:
                    meeting_id = str(meeting["id"])
                    # Simulate callback data format
                    callback_data = f"match_block_{meeting_id}_{test_user_id}"
                    print(f"\nTest user {test_user_id}:")
                    print(f"  Meeting ID: {meeting_id}")
                    print(f"  Callback data: {callback_data}")
                    
                    # Parse like in handler
                    parts = callback_data.replace("match_block_", "").split("_")
                    print(f"  Parsed parts: {parts}")
                    print(f"  Parts count: {len(parts)}")
                    
                    if len(parts) >= 2:
                        parsed_meeting_id = parts[0]
                        parsed_blocked_user_id = int(parts[1])
                        print(f"  Parsed meeting_id: {parsed_meeting_id}")
                        print(f"  Parsed blocked_user_id: {parsed_blocked_user_id}")
                        print(f"  ✓ Format is correct")
                    else:
                        print(f"  ✗ Format is incorrect")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(debug_callback_data())
