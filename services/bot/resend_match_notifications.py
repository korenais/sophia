"""
Script to resend match notifications for Anton Anisimov
Use this if notifications were not sent or need to be resent
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from db import get_pool, get_meeting_by_users, get_user_language
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Get DB_URL from environment
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5433/postgres")
if DB_URL:
    if "@db:" in DB_URL:
        DB_URL = DB_URL.replace("@db:5432", "@localhost:5433")
    elif "@localhost:5432" in DB_URL:
        DB_URL = DB_URL.replace("@localhost:5432", "@localhost:5433")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

ANTON_USER_ID = 1541686636
TEST_USER_IDS = [9000001, 9000002, 9000003]


async def resend_notifications():
    """Resend match notifications for Anton"""
    print("=" * 70)
    print("Resending match notifications for Anton Anisimov")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set. Cannot send notifications.")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Get Anton's info
        async with db_pool.acquire() as conn:
            anton_info = await conn.fetchrow(
                """
                SELECT user_id, intro_name, intro_location, intro_description, 
                       intro_linkedin, intro_image, user_telegram_link
                FROM public.users 
                WHERE user_id = $1
                """,
                ANTON_USER_ID
            )
            
            if not anton_info:
                print(f"[ERROR] Anton Anisimov (ID: {ANTON_USER_ID}) not found!")
                return
        
        # Send notifications for each test user
        for test_user_id in TEST_USER_IDS:
            try:
                # Get test user info
                async with db_pool.acquire() as conn:
                    test_user_info = await conn.fetchrow(
                        """
                        SELECT user_id, intro_name, intro_location, intro_description, 
                               intro_linkedin, intro_image, user_telegram_link
                        FROM public.users 
                        WHERE user_id = $1
                        """,
                        test_user_id
                    )
                    
                    if not test_user_info:
                        print(f"[WARNING] Test user {test_user_id} not found, skipping...")
                        continue
                    
                    # Get meeting ID
                    meeting = await conn.fetchrow(
                        """
                        SELECT id FROM public.meetings
                        WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        ANTON_USER_ID,
                        test_user_id
                    )
                    
                    if not meeting:
                        print(f"[WARNING] No meeting found for user {test_user_id}, skipping...")
                        continue
                    
                    meeting_id = str(meeting["id"])
                    
                    # Build and send notification directly
                    try:
                        from scenes import get_messages_dynamic
                        
                        messages = get_messages_dynamic()
                        match_msgs = messages.get("MATCH_NOTIFICATIONS", {})
                        user_lang = await get_user_language(db_pool, ANTON_USER_ID)
                        
                        # Build message using new format
                        matched_with_msg = match_msgs.get('MATCHED_WITH', 'Meet {name}! 👋')
                        location_msg = match_msgs.get('LOCATION', '📍 <b>Location:</b> {location}')
                        description_msg = match_msgs.get('DESCRIPTION', '💼 <b>About:</b> {description}')
                        
                        complete_message = (
                            f"{match_msgs.get('NEW_MATCH_TITLE', '🤝 <b>New Business Connection</b>')}\n\n"
                            f"{matched_with_msg.format(name=test_user_info.get('intro_name', 'Someone'))}\n\n"
                            f"{match_msgs.get('ABOUT_THEM', '<b>Profile Overview:</b>')}\n"
                            f"{location_msg.format(location=test_user_info.get('intro_location', 'Not specified'))}\n"
                            f"{description_msg.format(description=test_user_info.get('intro_description', 'No description'))}\n"
                        )
                        
                        # Add LinkedIn
                        if test_user_info.get('intro_linkedin'):
                            linkedin = test_user_info['intro_linkedin']
                            if not linkedin.startswith('http'):
                                linkedin_url = f"https://www.linkedin.com/in/{linkedin}" if not linkedin.startswith('/') else f"https://www.linkedin.com{linkedin}"
                            else:
                                linkedin_url = linkedin
                            linkedin_display = linkedin.split('/')[-1] if '/' in linkedin else linkedin
                            linkedin_display = linkedin_display.replace('in/', '').replace('@', '')
                            linkedin_msg = match_msgs.get('LINKEDIN', '🔗 <b>LinkedIn:</b> <a href="{linkedin_url}">{linkedin}</a>')
                            complete_message += f"{linkedin_msg.format(linkedin=linkedin_display, linkedin_url=linkedin_url)}\n"
                        
                        # Add profile link
                        frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
                        if not frontend_url:
                            frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
                        if frontend_url and test_user_id:
                            if "/api" in frontend_url or ":8055" in frontend_url:
                                base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
                                profile_url = f"{base_url}/#/user/{test_user_id}"
                            else:
                                profile_url = f"{frontend_url}/#/user/{test_user_id}"
                            profile_link_msg = match_msgs.get('PROFILE_LINK', '👤 <b>View Full Profile:</b> <a href="{profile_url}">Open Profile</a>')
                            complete_message += f"{profile_link_msg.format(profile_url=profile_url)}\n"
                        
                        # Add next steps
                        complete_message += (
                            f"\n{match_msgs.get('NEXT_STEPS', '<b>Next Steps:</b>')}\n"
                            f"{match_msgs.get('STEP_1', '💬 Contact via Telegram')}\n"
                            f"{match_msgs.get('STEP_2', '☕ Schedule a meeting')}\n"
                            f"{match_msgs.get('STEP_3', '🤝 Explore collaboration opportunities')}\n"
                        )
                        
                        # Add Telegram
                        if test_user_info.get('user_telegram_link'):
                            telegram_contact_msg = match_msgs.get('TELEGRAM_CONTACT', '💬 <b>Telegram:</b> <a href="https://t.me/{telegram_link}">@{telegram_link}</a>')
                            complete_message += f"\n{telegram_contact_msg.format(telegram_link=test_user_info['user_telegram_link'])}\n"
                        
                        complete_message += (
                            f"\n{match_msgs.get('VIEW_MATCHES_LATER', '<i>View all connections: /my_matches</i>')}\n\n"
                            f"{match_msgs.get('SUCCESS_MESSAGE', 'Best of luck with your networking! 🚀')}"
                        )
                        
                        # Create keyboard
                        if user_lang == 'ru':
                            button_met = "✅ Встреча состоялась"
                            button_block = "🚫 Исключить контакт"
                            button_disable = "⛔ Отключить рекомендации"
                        else:
                            button_met = "✅ Meeting completed"
                            button_block = "🚫 Exclude contact"
                            button_disable = "⛔ Disable recommendations"
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}")],
                            [InlineKeyboardButton(text=button_block, callback_data=f"match_block_{meeting_id}_{test_user_id}")],
                            [InlineKeyboardButton(text=button_disable, callback_data=f"match_disable_{meeting_id}")],
                        ])
                        
                        # Send directly using bot.send_message
                        sent = await bot.send_message(
                            chat_id=ANTON_USER_ID,
                            text=complete_message,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        print(f"[OK] Sent notification for {test_user_info['intro_name']} (Meeting ID: {meeting_id}, Message ID: {sent.message_id})")
                    except Exception as send_error:
                        print(f"[ERROR] Failed to send notification: {send_error}")
                        import traceback
                        traceback.print_exc()
                    
            except Exception as e:
                print(f"[ERROR] Error sending notification for user {test_user_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n[SUCCESS] Notifications sent!")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(resend_notifications())
