"""Enable matches and resend notifications"""
import asyncio
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
TEST_USER_IDS = [9000001, 9000002, 9000003]

async def enable_and_resend():
    """Enable matches and resend notifications"""
    print("=" * 70)
    print("Enable Matches and Resend Notifications")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        async with db_pool.acquire() as conn:
            # 1. Enable matches
            print("\n[STEP 1] Enabling matches for Anton...")
            await conn.execute(
                "UPDATE users SET matches_disabled = false, updated_at = NOW() WHERE user_id = $1",
                ANTON_USER_ID
            )
            print("  [OK] Matches enabled")
            
            # 2. Remove blocks
            print("\n[STEP 2] Removing match blocks...")
            for test_user_id in TEST_USER_IDS:
                await conn.execute(
                    """
                    DELETE FROM match_blocks
                    WHERE (user_id = $1 AND blocked_user_id = $2)
                       OR (user_id = $2 AND blocked_user_id = $1)
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
            print("  [OK] Blocks removed")
            
            # 3. Get language
            print("\n[STEP 3] Getting language settings...")
            bot_language = os.getenv("BOT_LANGUAGE", "ru")
            db_lang = await conn.fetchval(
                "SELECT language FROM users WHERE user_id = $1",
                ANTON_USER_ID
            ) or "ru"
            user_lang = bot_language if bot_language else db_lang
            print(f"  Using: {user_lang}")
            
            # 4. Prepare messages
            if user_lang == 'ru':
                button_profile = "👤 Открыть профиль"
                button_met = "✅ Встреча состоялась"
                button_block = "🚫 Исключить контакт"
                button_disable = "⛔ Отключить рекомендации"
                title = "🤝 <b>Новое бизнес-знакомство</b>"
                matched_with = "Мы подобрали для вас контакт: {name}"
                about_them = "<b>Краткая информация:</b>"
                location = "📍 <b>Местоположение:</b> {location}"
                description = "💼 <b>О себе:</b> {description}"
                linkedin = "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>"
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
                matched_with = "We've matched you with {name}"
                about_them = "<b>Profile Overview:</b>"
                location = "📍 <b>Location:</b> {location}"
                description = "💼 <b>About:</b> {description}"
                linkedin = "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>"
                next_steps = "<b>Next Steps:</b>"
                step1 = "💬 Contact via Telegram"
                step2 = "☕ Schedule a meeting"
                step3 = "🤝 Explore collaboration opportunities"
                telegram_contact = "💬 <b>Telegram:</b> <a href=\"https://t.me/{telegram_link}\">@{telegram_link}</a>"
                view_later = "📋 <i>View all connections: /my_matches</i>"
                success = "Best of luck with your networking! 🚀"
            
            # 5. Send notifications
            print("\n[STEP 4] Sending notifications...")
            sent_count = 0
            for test_user_id in TEST_USER_IDS:
                try:
                    test_user_info = await conn.fetchrow(
                        """
                        SELECT user_id, intro_name, intro_location, intro_description, 
                               intro_linkedin, user_telegram_link
                        FROM users 
                        WHERE user_id = $1
                        """,
                        test_user_id
                    )
                    
                    if not test_user_info:
                        print(f"  [WARNING] Test user {test_user_id} not found, skipping...")
                        continue
                    
                    meeting = await conn.fetchrow(
                        """
                        SELECT id FROM meetings
                        WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        ANTON_USER_ID,
                        test_user_id
                    )
                    
                    if not meeting:
                        print(f"  [WARNING] No meeting found for user {test_user_id}, skipping...")
                        continue
                    
                    meeting_id = str(meeting["id"])
                    test_user = dict(test_user_info)
                    
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
                    
                    if test_user.get('intro_linkedin'):
                        linkedin_val = test_user['intro_linkedin']
                        if not linkedin_val.startswith('http'):
                            linkedin_url_val = f"https://www.linkedin.com/in/{linkedin_val}" if not linkedin_val.startswith('/') else f"https://www.linkedin.com{linkedin_val}"
                        else:
                            linkedin_url_val = linkedin_val
                        linkedin_display = linkedin_val.split('/')[-1] if '/' in linkedin_val else linkedin_val
                        linkedin_display = linkedin_display.replace('in/', '').replace('@', '')
                        message_text += f"{linkedin.format(linkedin=linkedin_display, linkedin_url=linkedin_url_val)}\n"
                    
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
                    
                    frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
                    if not frontend_url:
                        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
                    
                    is_public_url = frontend_url and not any(host in frontend_url.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0'])
                    
                    profile_url = None
                    if frontend_url:
                        if "/api" in frontend_url or ":8055" in frontend_url:
                            base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
                            profile_url = f"{base_url}/%23/user/{test_user_id}"
                        else:
                            profile_url = f"{frontend_url}/%23/user/{test_user_id}"
                    
                    keyboard_buttons = []
                    
                    if profile_url and is_public_url:
                        if user_lang == 'ru':
                            profile_link_text = f"👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>\n"
                        else:
                            profile_link_text = f"👤 <b>Full Profile:</b> <a href=\"{profile_url}\">View Profile</a>\n"
                        message_text = message_text.replace(
                            f"\n{view_later}",
                            f"\n{profile_link_text}{view_later}"
                        )
                    else:
                        keyboard_buttons.append([
                            InlineKeyboardButton(text=button_profile, callback_data=f"view_profile_{test_user_id}"),
                        ])
                    
                    keyboard_buttons.append([
                        InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}"),
                    ])
                    keyboard_buttons.append([
                        InlineKeyboardButton(text=button_block, callback_data=f"match_block_{meeting_id}_{test_user_id}"),
                    ])
                    keyboard_buttons.append([
                        InlineKeyboardButton(text=button_disable, callback_data=f"match_disable_{meeting_id}"),
                    ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                    
                    sent = await bot.send_message(
                        chat_id=ANTON_USER_ID,
                        text=message_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    print(f"  [OK] Sent to {test_user['intro_name']} (Meeting: {meeting_id}, Message: {sent.message_id})")
                    sent_count += 1
                    
                except Exception as e:
                    print(f"  [ERROR] Failed to send to user {test_user_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"\n[SUCCESS] Sent {sent_count} notification(s)!")
            print(f"\nPlease check Telegram bot for user {ANTON_USER_ID}")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(enable_and_resend())

