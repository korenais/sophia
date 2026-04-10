"""Test notification with profile button"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ANTON_USER_ID = 1541686636
TEST_USER_ID = 9000002

async def test():
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5433/postgres")
    if "@db:" in DB_URL:
        DB_URL = DB_URL.replace("@db:5432", "@localhost:5433")
    elif "@localhost:5432" in DB_URL:
        DB_URL = DB_URL.replace("@localhost:5432", "@localhost:5433")
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    
    try:
        async with db_pool.acquire() as conn:
            # Get meeting ID
            meeting = await conn.fetchrow(
                """
                SELECT id FROM meetings
                WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
                ORDER BY created_at DESC LIMIT 1
                """,
                ANTON_USER_ID,
                TEST_USER_ID
            )
            
            if not meeting:
                print(f"[ERROR] No meeting found")
                return
            
            meeting_id = str(meeting["id"])
        
        # Create keyboard exactly as in match_system.py
        button_profile = "👤 Открыть профиль"
        button_met = "✅ Встреча состоялась"
        button_block = "🚫 Исключить контакт"
        button_disable = "⛔ Отключить рекомендации"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=button_profile, callback_data=f"view_profile_{TEST_USER_ID}"),
            ],
            [
                InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}"),
            ],
            [
                InlineKeyboardButton(text=button_block, callback_data=f"match_block_{meeting_id}_{TEST_USER_ID}"),
            ],
            [
                InlineKeyboardButton(text=button_disable, callback_data=f"match_disable_{meeting_id}"),
            ],
        ])
        
        message_text = """🤝 <b>Новое бизнес-знакомство</b>

Мы подобрали для вас контакт: <b>Test Business Partner 2</b>

<b>Краткая информация:</b>
📍 <b>Местоположение:</b> Tallinn, Estonia
💼 <b>О себе:</b> Entrepreneur and investor with focus on digital transformation

<b>Следующие шаги:</b>
💬 Связаться в Telegram
☕ Назначить встречу
🤝 Обсудить возможности сотрудничества

💬 <b>Telegram:</b> <a href="https://t.me/testuser9000002">@testuser9000002</a>

📋 <i>Все контакты: /my_matches</i>

Успешного нетворкинга! 🚀"""
        
        sent = await bot.send_message(
            chat_id=ANTON_USER_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        print(f"[OK] Test notification sent! Message ID: {sent.message_id}")
        print(f"[INFO] Check Telegram - button '👤 Открыть профиль' should be visible")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(test())
