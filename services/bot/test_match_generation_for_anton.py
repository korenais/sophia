"""Test match generation - should NOT create match for Anton if matches_disabled=True"""
import asyncio
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from match_system import MatchSystem
from aiogram import Bot

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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ANTON_USER_ID = 1541686636
TEST_USER_ID = 9000004

async def test():
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
    
    try:
        async with db_pool.acquire() as conn:
            print("=" * 70)
            print("Testing Match Generation with matches_disabled")
            print("=" * 70)
            
            # 1. Check Anton's status
            print("\n[STEP 1] Checking Anton's status...")
            anton_row = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state, finishedonboarding FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not anton_row:
                print(f"[ERROR] Anton not found!")
                return
            
            print(f"  User: {anton_row['intro_name']}")
            print(f"  matches_disabled: {anton_row['matches_disabled']}")
            print(f"  state: {anton_row['state']}")
            print(f"  finishedonboarding: {anton_row['finishedonboarding']}")
            
            # 2. Check test user
            print("\n[STEP 2] Checking test user...")
            test_user = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state, finishedonboarding FROM users WHERE user_id = $1",
                TEST_USER_ID
            )
            
            if not test_user:
                print(f"  [ERROR] Test user {TEST_USER_ID} not found!")
                return
            
            print(f"  User: {test_user['intro_name']}")
            print(f"  matches_disabled: {test_user['matches_disabled']}")
            print(f"  state: {test_user['state']}")
            print(f"  finishedonboarding: {test_user['finishedonboarding']}")
            
            # 3. Check existing meetings
            print("\n[STEP 3] Checking existing meetings...")
            existing_meeting = await conn.fetchrow(
                """
                SELECT id FROM meetings
                WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                """,
                ANTON_USER_ID,
                TEST_USER_ID
            )
            
            if existing_meeting:
                print(f"  [INFO] Existing meeting found: {existing_meeting['id']}")
                print(f"  [INFO] Deleting it for clean test...")
                await conn.execute("DELETE FROM meetings WHERE id = $1", existing_meeting['id'])
                print(f"  [OK] Deleted")
            else:
                print(f"  [OK] No existing meeting")
            
            # 4. Try to generate matches
            print("\n[STEP 4] Attempting to generate matches...")
            match_system = MatchSystem(bot, db_pool)
            matches = await match_system.generate_and_create_matches()
            
            print(f"  Generated {len(matches)} matches")
            
            # 5. Check if match was created for Anton
            print("\n[STEP 5] Checking if match was created for Anton...")
            new_meeting = await conn.fetchrow(
                """
                SELECT id FROM meetings
                WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                """,
                ANTON_USER_ID,
                TEST_USER_ID
            )
            
            if new_meeting:
                if anton_row['matches_disabled']:
                    print(f"  [ERROR] BUG: Match was created for Anton even though matches_disabled=True!")
                    print(f"  Meeting ID: {new_meeting['id']}")
                else:
                    print(f"  [OK] Match created (matches_disabled=False, so this is expected)")
                    print(f"  Meeting ID: {new_meeting['id']}")
            else:
                if anton_row['matches_disabled']:
                    print(f"  [OK] No match created for Anton (matches_disabled=True, correct behavior)")
                else:
                    print(f"  [INFO] No match created (may be due to other reasons)")
            
            # 6. Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Anton matches_disabled: {anton_row['matches_disabled']}")
            print(f"Match created for Anton: {new_meeting is not None}")
            if anton_row['matches_disabled'] and new_meeting:
                print("[ERROR] System is NOT respecting matches_disabled flag!")
            elif anton_row['matches_disabled'] and not new_meeting:
                print("[OK] System correctly respects matches_disabled flag - no match created")
            else:
                print("[INFO] Matches are enabled or other conditions not met")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()
        if bot:
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())

