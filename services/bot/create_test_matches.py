"""
Script to create test users and match recommendations for Anton Anisimov
This script creates test users and meetings to test the match recommendation buttons
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
import numpy as np

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from db import get_pool, create_meetings, get_matchable_users
from match_system import MatchSystem
from aiogram import Bot

# Get DB_URL from environment
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5433/postgres")
if DB_URL:
    if "@db:" in DB_URL:
        DB_URL = DB_URL.replace("@db:5432", "@localhost:5433")
    elif "@localhost:5432" in DB_URL:
        DB_URL = DB_URL.replace("@localhost:5432", "@localhost:5433")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")


async def find_anton_anisimov(db_pool):
    """Find user Anton Anisimov in database"""
    async with db_pool.acquire() as conn:
        # Try to find by name
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, state, finishedonboarding, vector_description
            FROM public.users
            WHERE LOWER(intro_name) LIKE '%anton%' AND LOWER(intro_name) LIKE '%anisimov%'
            OR LOWER(intro_name) LIKE '%антон%' AND LOWER(intro_name) LIKE '%анисимов%'
            LIMIT 1
            """
        )
        if row:
            return dict(row)
        
        # Try to find by partial name
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, state, finishedonboarding, vector_description
            FROM public.users
            WHERE LOWER(intro_name) LIKE '%anton%' OR LOWER(intro_name) LIKE '%антон%'
            ORDER BY user_id DESC
            LIMIT 1
            """
        )
        if row:
            return dict(row)
        
        return None


async def create_test_users(db_pool, anton_vector):
    """Create test users with similar vectors to Anton"""
    test_users = [
        {
            "name": "Test Business Partner 1",
            "location": "Riga, Latvia",
            "description": "Experienced business professional in technology and consulting",
            "linkedin": "test-partner-1",
            "vector": anton_vector if anton_vector else [0.1, 0.2, 0.3, 0.4, 0.5] * 100
        },
        {
            "name": "Test Business Partner 2",
            "location": "Tallinn, Estonia",
            "description": "Entrepreneur and investor with focus on digital transformation",
            "linkedin": "test-partner-2",
            "vector": anton_vector if anton_vector else [0.12, 0.22, 0.32, 0.42, 0.52] * 100
        },
        {
            "name": "Test Business Partner 3",
            "location": "Vilnius, Lithuania",
            "description": "Business development expert in fintech and innovation",
            "linkedin": "test-partner-3",
            "vector": anton_vector if anton_vector else [0.11, 0.21, 0.31, 0.41, 0.51] * 100
        }
    ]
    
    created_user_ids = []
    
    async with db_pool.acquire() as conn:
        for i, user_data in enumerate(test_users):
            user_id = 9000000 + i + 1  # Use high IDs to avoid conflicts
            
            await conn.execute(
                """
                INSERT INTO public.users (
                    user_id, chat_id, state, finishedonboarding, 
                    matches_disabled, vector_description, intro_name, 
                    intro_location, intro_description, intro_linkedin,
                    language, created_at, updated_at
                )
                VALUES ($1, $1, 'ACTIVE', true, false, $2, $3, $4, $5, $6, 'ru', NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET 
                    state = 'ACTIVE',
                    finishedOnboarding = true,
                    matches_disabled = false,
                    vector_description = $2,
                    intro_name = $3,
                    intro_location = $4,
                    intro_description = $5,
                    intro_linkedin = $6,
                    updated_at = NOW()
                """,
                user_id,
                user_data["vector"],
                user_data["name"],
                user_data["location"],
                user_data["description"],
                user_data["linkedin"]
            )
            
            created_user_ids.append(user_id)
            print(f"[OK] Created test user: {user_data['name']} (ID: {user_id})")
    
    return created_user_ids


async def create_meetings_for_anton(db_pool, anton_user_id, test_user_ids):
    """Create meetings between Anton and test users"""
    pairs = [(anton_user_id, test_user_id) for test_user_id in test_user_ids]
    meeting_ids = await create_meetings(db_pool, pairs)
    
    print(f"[OK] Created {len(meeting_ids)} meetings for Anton Anisimov")
    return meeting_ids


async def send_match_notifications(bot, db_pool, anton_user_id, test_user_ids):
    """Send match notifications to Anton using MatchSystem"""
    from match_system import MatchSystem
    
    match_system = MatchSystem(bot, db_pool)
    
    # Get user info for notifications
    async with db_pool.acquire() as conn:
        anton_info = await conn.fetchrow(
            """
            SELECT user_id, intro_name, intro_location, intro_description, 
                   intro_linkedin, intro_image, user_telegram_link
            FROM public.users 
            WHERE user_id = $1
            """,
            anton_user_id
        )
        
        test_users_info = []
        for test_user_id in test_user_ids:
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, intro_location, intro_description, 
                       intro_linkedin, intro_image, user_telegram_link
                FROM public.users 
                WHERE user_id = $1
                """,
                test_user_id
            )
            if row:
                test_users_info.append(dict(row))
    
    # Send notifications for each test user
    async with db_pool.acquire() as conn:
        for test_user_info in test_users_info:
            try:
                # Get meeting ID
                meeting = await conn.fetchrow(
                    """
                    SELECT id FROM public.meetings
                    WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    anton_user_id,
                    test_user_info["user_id"]
                )
                
                if meeting:
                    meeting_id = str(meeting["id"])
                    await match_system._send_match_notification(
                        anton_user_id,
                        dict(anton_info) if anton_info else {},
                        test_user_info,
                        meeting_id,
                        test_user_info["user_id"]
                    )
                    print(f"[OK] Sent match notification for {test_user_info['intro_name']}")
            except Exception as e:
                print(f"[ERROR] Error sending notification for {test_user_info.get('intro_name', 'unknown')}: {e}")


async def main():
    """Main function"""
    print("=" * 70)
    print("Creating test matches for Anton Anisimov")
    print("=" * 70)
    
    # Create database pool
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        # Step 1: Find Anton Anisimov
        print("\n[STEP 1] Looking for Anton Anisimov...")
        anton = await find_anton_anisimov(db_pool)
        
        if not anton:
            print("[ERROR] Anton Anisimov not found in database!")
            print("   Please make sure the user exists and has completed onboarding.")
            return
        
        anton_user_id = anton["user_id"]
        anton_name = anton.get("intro_name", "Anton Anisimov")
        anton_vector = anton.get("vector_description")
        
        print(f"[OK] Found user: {anton_name} (ID: {anton_user_id})")
        print(f"   State: {anton.get('state', 'UNKNOWN')}")
        print(f"   Finished onboarding: {anton.get('finishedonboarding', False)}")
        print(f"   Has vector: {anton_vector is not None}")
        
        if anton.get("state") != "ACTIVE":
            print(f"[WARNING] User state is '{anton.get('state')}', should be 'ACTIVE' for matches")
        
        if not anton.get("finishedonboarding"):
            print("[WARNING] User hasn't finished onboarding")
            print("[INFO] Setting finishedonboarding = true for testing...")
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true WHERE user_id = $1",
                    anton_user_id
                )
            print("[OK] Updated finishedonboarding to true")
        
        if not anton_vector:
            print("[WARNING] User doesn't have vector_description")
        
        # Step 2: Create test users
        print("\n[STEP 2] Creating test users...")
        test_user_ids = await create_test_users(db_pool, anton_vector)
        
        # Step 3: Create meetings
        print("\n[STEP 3] Creating meetings...")
        meeting_ids = await create_meetings_for_anton(db_pool, anton_user_id, test_user_ids)
        
        # Step 4: Send notifications (if bot token is available)
        if TELEGRAM_TOKEN:
            print("\n[STEP 4] Sending match notifications...")
            bot = Bot(token=TELEGRAM_TOKEN)
            try:
                await send_match_notifications(bot, db_pool, anton_user_id, test_user_ids)
            except Exception as e:
                print(f"[ERROR] Error sending notifications: {e}")
            finally:
                await bot.session.close()
        else:
            print("\n[STEP 4] Skipping notifications (TELEGRAM_TOKEN not set)")
            print("   Meetings are created. You can trigger notifications manually or wait for scheduler.")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] Setup complete!")
        print("=" * 70)
        print(f"\nCreated {len(test_user_ids)} test users and {len(meeting_ids)} meetings")
        print(f"Anton Anisimov (ID: {anton_user_id}) should receive match recommendations")
        print("\nTest user IDs:")
        for i, user_id in enumerate(test_user_ids, 1):
            print(f"  {i}. User ID: {user_id}")
        print("\nMeeting IDs:")
        for i, meeting_id in enumerate(meeting_ids, 1):
            print(f"  {i}. Meeting ID: {meeting_id}")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
