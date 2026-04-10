"""Test matches_disabled flag functionality"""
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

async def test():
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        async with db_pool.acquire() as conn:
            # 1. Check current status
            print("=" * 70)
            print("Testing matches_disabled functionality")
            print("=" * 70)
            
            print("\n[STEP 1] Checking Anton's current status...")
            user_row = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state, finishedonboarding FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not user_row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print(f"  User: {user_row['intro_name']}")
            print(f"  matches_disabled: {user_row['matches_disabled']}")
            print(f"  state: {user_row['state']}")
            print(f"  finishedonboarding: {user_row['finishedonboarding']}")
            
            # 2. Check if Anton is in matchable users list
            print("\n[STEP 2] Checking if Anton is in matchable users...")
            from db import get_matchable_users
            matchable_users = await get_matchable_users(db_pool)
            anton_in_list = any(u['user_id'] == ANTON_USER_ID for u in matchable_users)
            
            print(f"  Total matchable users: {len(matchable_users)}")
            print(f"  Anton in matchable list: {anton_in_list}")
            
            if anton_in_list:
                print("  [WARNING] Anton is in matchable users list!")
                if user_row['matches_disabled']:
                    print("  [ERROR] But matches_disabled = True! This is a bug!")
            else:
                if user_row['matches_disabled']:
                    print("  [OK] Anton is correctly excluded (matches_disabled = True)")
                else:
                    print("  [INFO] Anton is not in list for other reasons (check state/onboarding)")
            
            # 3. Test: Create a new test user and try to generate match
            print("\n[STEP 3] Testing match generation with matches_disabled...")
            
            # Check if test user exists
            test_user_id = 9000004
            test_user = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled FROM users WHERE user_id = $1",
                test_user_id
            )
            
            if not test_user:
                print(f"  [INFO] Creating test user {test_user_id}...")
                # Create a simple test user
                await conn.execute(
                    """
                    INSERT INTO users (user_id, intro_name, state, finishedonboarding, vector_description, matches_disabled)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE SET
                        intro_name = EXCLUDED.intro_name,
                        state = EXCLUDED.state,
                        finishedonboarding = EXCLUDED.finishedonboarding,
                        vector_description = EXCLUDED.vector_description,
                        matches_disabled = EXCLUDED.matches_disabled
                    """,
                    test_user_id,
                    "Test User for Match",
                    "ACTIVE",
                    True,
                    [0.1, 0.2, 0.3, 0.4, 0.5],  # Simple vector
                    False  # Matches enabled
                )
                print(f"  [OK] Test user created")
            else:
                print(f"  [INFO] Test user {test_user_id} already exists")
                print(f"    Name: {test_user['intro_name']}")
                print(f"    matches_disabled: {test_user['matches_disabled']}")
            
            # 4. Check if match would be generated
            print("\n[STEP 4] Checking if match would be generated...")
            matchable_after = await get_matchable_users(db_pool)
            print(f"  Matchable users: {len(matchable_after)}")
            
            anton_would_match = any(u['user_id'] == ANTON_USER_ID for u in matchable_after)
            test_would_match = any(u['user_id'] == test_user_id for u in matchable_after)
            
            print(f"  Anton would be matched: {anton_would_match}")
            print(f"  Test user would be matched: {test_would_match}")
            
            if user_row['matches_disabled'] and anton_would_match:
                print("  [ERROR] BUG: Anton has matches_disabled=True but is in matchable list!")
            elif user_row['matches_disabled'] and not anton_would_match:
                print("  [OK] System correctly excludes Anton (matches_disabled=True)")
            
            # 5. Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Anton matches_disabled: {user_row['matches_disabled']}")
            print(f"Anton in matchable list: {anton_would_match}")
            if user_row['matches_disabled']:
                if anton_would_match:
                    print("[ERROR] System is NOT respecting matches_disabled flag!")
                else:
                    print("[OK] System correctly respects matches_disabled flag")
            else:
                print("[INFO] Matches are enabled for Anton")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(test())

