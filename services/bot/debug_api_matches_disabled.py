"""Debug why API returns None for matches_disabled"""
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

async def debug():
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        async with db_pool.acquire() as conn:
            print("=" * 70)
            print("Debugging matches_disabled in database")
            print("=" * 70)
            
            # Check what database returns
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, intro_location, intro_description, intro_linkedin, 
                       intro_hobbies_drivers, intro_skills, intro_birthday, intro_image, 
                       user_telegram_link, state, notifications_enabled, matches_disabled
                FROM users WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            
            if not row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print(f"\nDirect database query result:")
            print(f"  matches_disabled: {row['matches_disabled']}")
            print(f"  Type: {type(row['matches_disabled'])}")
            print(f"  Is True: {row['matches_disabled'] is True}")
            print(f"  Is False: {row['matches_disabled'] is False}")
            print(f"  Is None: {row['matches_disabled'] is None}")
            
            # Convert to dict like API does
            user_dict = dict(row)
            print(f"\nAfter dict(row):")
            print(f"  matches_disabled: {user_dict.get('matches_disabled')}")
            print(f"  Type: {type(user_dict.get('matches_disabled'))}")
            
            # Simulate process_user_data
            if user_dict.get("matches_disabled") is None:
                user_dict["matches_disabled"] = False
                print(f"\nAfter process_user_data normalization (if None -> False):")
                print(f"  matches_disabled: {user_dict.get('matches_disabled')}")
            else:
                print(f"\nAfter process_user_data (value preserved):")
                print(f"  matches_disabled: {user_dict.get('matches_disabled')}")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(debug())
