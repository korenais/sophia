"""Test profile link in actual message"""
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
        # Test with actual URL formation
        frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
        if not frontend_url:
            frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
        
        test_user_id = 9000001
        if frontend_url:
            if "/api" in frontend_url or ":8055" in frontend_url:
                base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
                profile_url = f"{base_url}/#/user/{test_user_id}"
            else:
                profile_url = f"{frontend_url}/#/user/{test_user_id}"
        else:
            profile_url = f"http://localhost:8081/#/user/{test_user_id}"
        
        print(f"Profile URL: {profile_url}")
        
        # Test name link
        match_name = "Test User"
        telegram_username = "testuser9000001"
        name_display = f'<a href="https://t.me/{telegram_username}">{match_name}</a>'
        
        # Test profile link
        profile_link = f"👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"
        
        message_text = (
            "🤝 <b>Новое бизнес-знакомство</b>\n\n"
            f"Мы подобрали для вас контакт: {name_display}\n\n"
            "<b>Краткая информация:</b>\n"
            "📍 <b>Местоположение:</b> Test Location\n"
            "💼 <b>О себе:</b> Test Description\n"
            f"{profile_link}\n"
        )
        
        print("\nMessage text preview (first 200 chars):")
        try:
            print(message_text[:200] + "...")
        except:
            print("(Cannot print due to encoding)")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Встреча состоялась", callback_data="match_met_1330")],
        ])
        
        sent = await bot.send_message(
            chat_id=ANTON_USER_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        print(f"\n[OK] Test message sent! Message ID: {sent.message_id}")
        print(f"[INFO] Check Telegram - both name and profile link should be clickable")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
