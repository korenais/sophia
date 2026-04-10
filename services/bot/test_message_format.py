"""Test message format to check HTML links"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ANTON_USER_ID = 1541686636

async def test():
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Test message with clickable name and profile link
        test_name = "Test User"
        telegram_link = "testuser9000001"
        profile_url = "http://localhost:8081/#/user/9000001"
        
        message_text = (
            "🤝 <b>Новое бизнес-знакомство</b>\n\n"
            f"Мы подобрали для вас контакт: <a href=\"https://t.me/{telegram_link}\">{test_name}</a>\n\n"
            "<b>Краткая информация:</b>\n"
            "📍 <b>Местоположение:</b> Test Location\n"
            "💼 <b>О себе:</b> Test Description\n"
            f"👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Встреча состоялась", callback_data="match_met_1330")],
            [InlineKeyboardButton(text="🚫 Исключить контакт", callback_data="match_block_1330_9000001")],
            [InlineKeyboardButton(text="⛔ Отключить рекомендации", callback_data="match_disable_1330")],
        ])
        
        sent = await bot.send_message(
            chat_id=ANTON_USER_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        print(f"[OK] Test message sent! Message ID: {sent.message_id}")
        print(f"[INFO] Check Telegram - name and profile link should be clickable")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
