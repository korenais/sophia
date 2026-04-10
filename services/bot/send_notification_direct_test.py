"""Direct test to send notification to Anton to check if messages are delivered"""
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

async def send_test():
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN not set")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Send simple test message
        test_message = (
            "🤝 <b>Тестовое сообщение</b>\n\n"
            "Это тестовое сообщение для проверки доставки.\n\n"
            "Если вы видите это сообщение, значит бот может отправлять вам сообщения."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Тест", callback_data="test_button")]
        ])
        
        try:
            sent = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text=test_message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            print(f"[OK] Test message sent! Message ID: {sent.message_id}")
            print(f"[INFO] Check Telegram bot for user {ANTON_USER_ID}")
        except Exception as e:
            print(f"[ERROR] Failed to send test message: {e}")
            print(f"[INFO] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(send_test())
