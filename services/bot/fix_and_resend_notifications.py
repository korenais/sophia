"""
Comprehensive script to check and fix all issues, then resend notifications
"""
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

async def fix_and_resend():
    """Check everything and resend notifications"""
    print("=" * 70)
    print("Comprehensive Fix and Resend Notifications")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        async with db_pool.acquire() as conn:
            # 1. Check user status
            print("\n[STEP 1] Checking user status...")
            user_row = await conn.fetchrow(
                "SELECT user_id, intro_name, matches_disabled, state, finishedonboarding, notifications_enabled FROM users WHERE user_id = $1",
                ANTON_USER_ID
            )
            
            if not user_row:
                print(f"[ERROR] User {ANTON_USER_ID} not found!")
                return
            
            print(f"  User: {user_row['intro_name']}")
            print(f"  matches_disabled: {user_row['matches_disabled']}")
            print(f"  state: {user_row['state']}")
            print(f"  finishedonboarding: {user_row['finishedonboarding']}")
            print(f"  notifications_enabled: {user_row['notifications_enabled']}")
            
            # 2. Fix user status if needed (but preserve matches_disabled if user disabled it)
            print("\n[STEP 2] Fixing user status if needed...")
            fixes = []
            # NOTE: Do NOT reset matches_disabled - respect user's choice if they disabled matches
            
            if user_row['state'] != 'ACTIVE':
                await conn.execute(
                    "UPDATE users SET state = 'ACTIVE', updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                fixes.append(f"Set state to ACTIVE (was {user_row['state']})")
            
            if not user_row['finishedonboarding']:
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                fixes.append("Set finishedonboarding to true")
            
            if not user_row['notifications_enabled']:
                await conn.execute(
                    "UPDATE users SET notifications_enabled = true, updated_at = NOW() WHERE user_id = $1",
                    ANTON_USER_ID
                )
                fixes.append("Enabled notifications")
            
            if fixes:
                print(f"  [OK] Applied fixes: {', '.join(fixes)}")
            else:
                print("  [OK] No fixes needed")
            
            # Check if matches are disabled and warn
            if user_row['matches_disabled']:
                print(f"  [INFO] Matches are disabled for this user - notifications will NOT be sent")
            
            # 3. Check and remove blocks
            print("\n[STEP 3] Checking match blocks...")
            for test_user_id in TEST_USER_IDS:
                block = await conn.fetchrow(
                    """
                    SELECT id FROM match_blocks
                    WHERE (user_id = $1 AND blocked_user_id = $2)
                       OR (user_id = $2 AND blocked_user_id = $1)
                    """,
                    ANTON_USER_ID,
                    test_user_id
                )
                
                if block:
                    await conn.execute(
                        """
                        DELETE FROM match_blocks
                        WHERE (user_id = $1 AND blocked_user_id = $2)
                           OR (user_id = $2 AND blocked_user_id = $1)
                        """,
                        ANTON_USER_ID,
                        test_user_id
                    )
                    test_user_name = await conn.fetchval(
                        "SELECT intro_name FROM users WHERE user_id = $1",
                        test_user_id
                    )
                    print(f"  [OK] Removed block for {test_user_name} (ID: {test_user_id})")
                else:
                    test_user_name = await conn.fetchval(
                        "SELECT intro_name FROM users WHERE user_id = $1",
                        test_user_id
                    )
                    print(f"  [OK] No block for {test_user_name} (ID: {test_user_id})")
            
            # 4. Get language
            print("\n[STEP 4] Getting language settings...")
            bot_language = os.getenv("BOT_LANGUAGE", "ru")
            db_lang = await conn.fetchval(
                "SELECT language FROM users WHERE user_id = $1",
                ANTON_USER_ID
            ) or "ru"
            user_lang = bot_language if bot_language else db_lang
            print(f"  BOT_LANGUAGE: {bot_language}")
            print(f"  DB language: {db_lang}")
            print(f"  Using: {user_lang}")
            
            # 5. Prepare messages
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
                matched_with = "We've matched you with {name}"
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
            
            # 6. Check if matches are disabled - if so, skip sending
            if user_row['matches_disabled']:
                print("\n[STEP 5] Skipping notifications...")
                print("  [SKIP] Matches are disabled for this user. Notifications will not be sent.")
                print("  [INFO] To enable matches, use /enable_matches command in bot or admin panel")
                return
            
            # 7. Send notifications
            print("\n[STEP 5] Sending notifications...")
            sent_count = 0
            for test_user_id in TEST_USER_IDS:
                try:
                    # Get test user info
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
                    
                    # Get meeting ID
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
                    
                    # Build message
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
                    
                    # Add LinkedIn
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
                    
                    # Build frontend profile URL for URL button or text link
                    frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
                    if not frontend_url:
                        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
                    
                    # Check if frontend URL is public (not localhost)
                    is_public_url = frontend_url and not any(host in frontend_url.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0'])
                    
                    # Create profile URL - encode # as %23 for Telegram
                    profile_url = None
                    if frontend_url:
                        if "/api" in frontend_url or ":8055" in frontend_url:
                            base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
                            profile_url = f"{base_url}/%23/user/{test_user_id}"
                        else:
                            profile_url = f"{frontend_url}/%23/user/{test_user_id}"
                    
                    # Add profile link to message text if we have a public URL, otherwise use callback button
                    keyboard_buttons = []
                    
                    if profile_url and is_public_url:
                        # Use URL link in text for public URLs
                        if user_lang == 'ru':
                            profile_link_text = f"👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>\n"
                        else:
                            profile_link_text = f"👤 <b>Full Profile:</b> <a href=\"{profile_url}\">View Profile</a>\n"
                        # Insert profile link before "View all connections" line
                        message_text = message_text.replace(
                            f"\n{view_later}",
                            f"\n{profile_link_text}{view_later}"
                        )
                    else:
                        # Use callback button for localhost or if no URL
                        keyboard_buttons.append([
                            InlineKeyboardButton(text=button_profile, callback_data=f"view_profile_{test_user_id}"),
                        ])
                    
                    # Action buttons - one per row for better readability
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
                    
                    # Send message
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
    asyncio.run(fix_and_resend())
