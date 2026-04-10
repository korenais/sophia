"""
Direct script to send test match notifications with buttons to Anton Anisimov
This script sends notifications directly using bot.send_message to ensure delivery
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

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


async def send_direct_notifications():
    """Send match notifications directly to Anton"""
    print("=" * 70)
    print("Sending direct match notifications to Anton Anisimov")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set. Cannot send notifications.")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Get user language - prefer BOT_LANGUAGE from env, fallback to user's language in DB
        bot_language = os.getenv("BOT_LANGUAGE", "ru")
        async with db_pool.acquire() as conn:
            user_lang_row = await conn.fetchrow(
                "SELECT language FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            db_lang = user_lang_row["language"] if user_lang_row and user_lang_row["language"] else "ru"
            # Use BOT_LANGUAGE if set, otherwise use user's language from DB
            user_lang = bot_language if bot_language else db_lang
            print(f"[INFO] Using language: {user_lang} (BOT_LANGUAGE={bot_language}, DB language={db_lang})")
        
        # Prepare button texts based on language
        if user_lang == 'ru':
            button_profile = "👤 Открыть профиль"
            button_met = "✅ Встреча состоялась"
            button_block = "🚫 Исключить контакт"
            button_disable = "⛔ Отключить рекомендации"
            title = "🤝 <b>Новое бизнес-знакомство</b>"
            matched_with = "Мы подобрали для вас контакт: <b>{name}</b>"
            about_them = "<b>Краткая информация:</b>"
            location = "📍 <b>Местоположение:</b> {location}"
            description = "💼 <b>О себе:</b> {description}"
            linkedin = "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>"
            # Profile link removed - using inline button instead
            next_steps = "<b>Следующие шаги:</b>"
            step1 = "💬 Связаться в Telegram"
            step2 = "☕ Назначить встречу"
            step3 = "🤝 Обсудить возможности сотрудничества"
            telegram_contact = "💬 <b>Telegram:</b> <a href=\"https://t.me/{telegram_link}\">@{telegram_link}</a>"
            view_later = "📋 <i>Все контакты: /my_matches</i>"
            success = "Успешного нетворкинга! 🚀"
        else:
            button_profile = "👤 View Profile"
            button_met = "✅ Meeting completed"
            button_block = "🚫 Exclude contact"
            button_disable = "⛔ Disable recommendations"
            title = "🤝 <b>New Business Connection</b>"
            matched_with = "We've matched you with <b>{name}</b>"
            about_them = "<b>Profile Overview:</b>"
            location = "📍 <b>Location:</b> {location}"
            description = "💼 <b>About:</b> {description}"
            linkedin = "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>"
            # Profile link removed - using inline button instead
            next_steps = "<b>Next Steps:</b>"
            step1 = "💬 Contact via Telegram"
            step2 = "☕ Schedule a meeting"
            step3 = "🤝 Explore collaboration opportunities"
            telegram_contact = "💬 <b>Telegram:</b> <a href=\"https://t.me/{telegram_link}\">@{telegram_link}</a>"
            view_later = "📋 <i>View all connections: /my_matches</i>"
            success = "Best of luck with your networking! 🚀"
        
        # Send notifications for each test user
        for test_user_id in TEST_USER_IDS:
            try:
                async with db_pool.acquire() as conn:
                    # Get test user info
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
                    test_user = dict(test_user_info)
                    
                    # Build message with improved format
                    # Make name clickable if Telegram link is available
                    match_name = test_user.get('intro_name', 'Someone')
                    match_telegram_link = test_user.get('user_telegram_link')
                    
                    if match_telegram_link:
                        telegram_username = match_telegram_link.replace('@', '')
                        name_display = f'<a href="https://t.me/{telegram_username}">{match_name}</a>'
                    else:
                        name_display = f'<b>{match_name}</b>'
                    
                    message_text = (
                        f"{title}\n\n"
                        f"{matched_with.format(name=name_display)}\n\n"
                        f"{about_them}\n"
                        f"{location.format(location=test_user.get('intro_location', 'Not specified'))}\n"
                        f"{description.format(description=test_user.get('intro_description', 'No description'))}\n"
                    )
                    
                    # Add LinkedIn with proper URL formatting
                    if test_user.get('intro_linkedin'):
                        linkedin_val = test_user['intro_linkedin']
                        if not linkedin_val.startswith('http'):
                            linkedin_url_val = f"https://www.linkedin.com/in/{linkedin_val}" if not linkedin_val.startswith('/') else f"https://www.linkedin.com{linkedin_val}"
                        else:
                            linkedin_url_val = linkedin_val
                        linkedin_display = linkedin_val.split('/')[-1] if '/' in linkedin_val else linkedin_val
                        linkedin_display = linkedin_display.replace('in/', '').replace('@', '')
                        message_text += f"{linkedin.format(linkedin=linkedin_display, linkedin_url=linkedin_url_val)}\n"
                    
                    # Profile link removed - using inline button instead
                    
                    message_text += (
                        f"\n{next_steps}\n"
                        f"{step1}\n"
                        f"{step2}\n"
                        f"{step3}\n"
                    )
                    
                    if test_user.get('user_telegram_link'):
                        message_text += f"\n{telegram_contact.format(telegram_link=test_user['user_telegram_link'])}\n"
                    
                    message_text += (
                        f"\n{view_later}\n\n"
                        f"{success}"
                    )
                    
                    # Create keyboard
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text=button_profile, callback_data=f"view_profile_{test_user_id}"),
                        ],
                        [
                            InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}"),
                        ],
                        [
                            InlineKeyboardButton(text=button_block, callback_data=f"match_block_{meeting_id}_{test_user_id}"),
                        ],
                        [
                            InlineKeyboardButton(text=button_disable, callback_data=f"match_disable_{meeting_id}"),
                        ],
                    ])
                    
                    # Send message directly
                    try:
                        sent_message = await bot.send_message(
                            chat_id=ANTON_USER_ID,
                            text=message_text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        print(f"[OK] Sent notification for {test_user['intro_name']} (Meeting ID: {meeting_id}, Message ID: {sent_message.message_id})")
                    except Exception as e:
                        print(f"[ERROR] Failed to send message for {test_user['intro_name']}: {e}")
                        import traceback
                        traceback.print_exc()
                    
            except Exception as e:
                print(f"[ERROR] Error processing user {test_user_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n[SUCCESS] All notifications sent!")
        print("\nPlease check Telegram bot for Anton Anisimov (ID: 1541686636)")
        print("You should see 3 messages with match recommendations and buttons.")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(send_direct_notifications())
