"""Check match blocks and matches_disabled status for Anton"""
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

async def check_blocks():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Check matches_disabled
            user_row = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not user_row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print("=" * 70)
            print(f"User: {user_row['intro_name']} (ID: {ANTON_USER_ID})")
            print("=" * 70)
            print(f"matches_disabled: {user_row['matches_disabled']}")
            print(f"state: {user_row['state']}")
            
            # Check match blocks
            print("\n" + "=" * 70)
            print("Checking match blocks...")
            print("=" * 70)
            
            blocks = await conn.fetch(
                """
                SELECT mb.id, mb.user_id, mb.blocked_user_id, mb.created_at,
                       u1.intro_name as user_name, u2.intro_name as blocked_user_name
                FROM match_blocks mb
                LEFT JOIN users u1 ON mb.user_id = u1.user_id
                LEFT JOIN users u2 ON mb.blocked_user_id = u2.user_id
                WHERE mb.user_id = $1 OR mb.blocked_user_id = $1
                ORDER BY mb.created_at DESC
                """,
                ANTON_USER_ID
            )
            
            if blocks:
                print(f"\n[WARNING] Found {len(blocks)} block(s):")
                for block in blocks:
                    print(f"  - Block ID: {block['id']}")
                    print(f"    User: {block['user_name']} (ID: {block['user_id']})")
                    print(f"    Blocked User: {block['blocked_user_name']} (ID: {block['blocked_user_id']})")
                    print(f"    Created: {block['created_at']}")
                    print()
            else:
                print("[OK] No match blocks found")
            
            # Check blocks for test users specifically
            print("\n" + "=" * 70)
            print("Checking blocks for test users...")
            print("=" * 70)
            
            for test_user_id in TEST_USER_IDS:
                block = await conn.fetchrow(
                    """
                    SELECT mb.id, mb.user_id, mb.blocked_user_id, mb.created_at
                    FROM match_blocks mb
                    WHERE (mb.user_id = $1 AND mb.blocked_user_id = $2)
                       OR (mb.user_id = $2 AND mb.blocked_user_id = $1)
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
                
                test_user_name = await conn.fetchval(
                    "SELECT intro_name FROM users WHERE user_id = $1",
                    test_user_id
                )
                
                if block:
                    print(f"[WARNING] Test user {test_user_id} ({test_user_name}) is BLOCKED!")
                    print(f"  Block ID: {block['id']}, Created: {block['created_at']}")
                else:
                    print(f"[OK] Test user {test_user_id} ({test_user_name}) is NOT blocked")
            
            # Fix issues
            print("\n" + "=" * 70)
            print("Fixing issues...")
            print("=" * 70)
            
            # Enable matches if disabled
            if user_row['matches_disabled']:
                print("\n[FIX] Enabling matches...")
                await conn.execute(
                    "UPDATE users SET matches_disabled = false, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] Matches enabled!")
            
            # Remove blocks for test users
            removed_count = 0
            for test_user_id in TEST_USER_IDS:
                result = await conn.execute(
                    """
                    DELETE FROM match_blocks
                    WHERE (user_id = $1 AND blocked_user_id = $2)
                       OR (user_id = $2 AND blocked_user_id = $1)
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
                if "DELETE" in result:
                    count = int(result.split()[-1])
                    if count > 0:
                        removed_count += count
                        test_user_name = await conn.fetchval(
                            "SELECT intro_name FROM users WHERE user_id = $1",
                            test_user_id
                        )
                        print(f"[OK] Removed block for test user {test_user_id} ({test_user_name})")
            
            if removed_count > 0:
                print(f"\n[SUCCESS] Removed {removed_count} block(s)")
            else:
                print("\n[OK] No blocks to remove")
            
            # Final status
            print("\n" + "=" * 70)
            print("Final Status")
            print("=" * 70)
            final_user = await conn.fetchrow(
                "SELECT matches_disabled, state FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print(f"matches_disabled: {final_user['matches_disabled']}")
            print(f"state: {final_user['state']}")
            
            final_blocks = await conn.fetchval(
                """
                SELECT COUNT(*) FROM match_blocks
                WHERE user_id = $1 OR blocked_user_id = $1
                """,
                ANTON_USER_ID
            )
            print(f"Total blocks: {final_blocks}")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(check_blocks())
