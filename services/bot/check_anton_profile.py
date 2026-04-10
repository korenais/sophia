"""Check Anton's profile status and onboarding completion"""
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

async def check_profile():
    pool = await asyncpg.create_pool(dsn=DB_URL)
    try:
        async with pool.acquire() as conn:
            # Get all profile fields
            user = await conn.fetchrow(
                """
                SELECT 
                    user_id, intro_name, intro_location, intro_description,
                    intro_linkedin, intro_hobbies_drivers, intro_skills,
                    field_of_activity, intro_birthday, intro_image,
                    finishedonboarding, state, language, matches_disabled
                FROM users 
                WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            
            if not user:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print("=" * 70)
            print(f"Profile Status for: {user['intro_name']} (ID: {ANTON_USER_ID})")
            print("=" * 70)
            
            print(f"\nfinishedOnboarding: {user['finishedonboarding']}")
            print(f"state: {user['state']}")
            print(f"matches_disabled: {user['matches_disabled']}")
            
            print("\n" + "=" * 70)
            print("Profile Fields:")
            print("=" * 70)
            
            fields = {
                'intro_name': user.get('intro_name'),
                'intro_location': user.get('intro_location'),
                'intro_description': user.get('intro_description'),
                'intro_linkedin': user.get('intro_linkedin'),
                'intro_hobbies_drivers': user.get('intro_hobbies_drivers'),
                'intro_skills': user.get('intro_skills'),
                'field_of_activity': user.get('field_of_activity'),
                'intro_birthday': user.get('intro_birthday'),
                'intro_image': 'SET' if user.get('intro_image') else 'NOT SET'
            }
            
            missing_fields = []
            for field, value in fields.items():
                status = "OK" if value else "MISSING"
                if not value:
                    missing_fields.append(field)
                print(f"  {field}: {value if value else '[EMPTY]'} [{status}]")
            
            print("\n" + "=" * 70)
            print("Analysis:")
            print("=" * 70)
            
            if not user['finishedonboarding']:
                print("\n[WARNING] finishedOnboarding is FALSE!")
                print(f"Missing fields: {missing_fields}")
                
                # Check what's required for onboarding
                print("\n[INFO] Attempting to fix...")
                
                # Set finishedonboarding to true (lowercase)
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] Set finishedonboarding = true")
                
                # Verify
                updated = await conn.fetchval(
                    "SELECT finishedonboarding FROM users WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print(f"[VERIFY] finishedonboarding is now: {updated}")
            else:
                print("\n[OK] finishedOnboarding is TRUE")
            
            if user['state'] != 'ACTIVE':
                print(f"\n[WARNING] state is '{user['state']}', should be 'ACTIVE'")
                await conn.execute(
                    "UPDATE users SET state = 'ACTIVE', updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] Set state = 'ACTIVE'")
            
            if user['matches_disabled']:
                print(f"\n[WARNING] matches_disabled is TRUE")
                await conn.execute(
                    "UPDATE users SET matches_disabled = false, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                print("[OK] Set matches_disabled = false")
            
            # Final status
            print("\n" + "=" * 70)
            print("Final Status:")
            print("=" * 70)
            final = await conn.fetchrow(
                "SELECT finishedonboarding, state, matches_disabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            print(f"finishedOnboarding: {final['finishedonboarding']}")
            print(f"state: {final['state']}")
            print(f"matches_disabled: {final['matches_disabled']}")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(check_profile())
