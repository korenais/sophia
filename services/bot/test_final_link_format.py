"""Final test for profile link formatting"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot

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
        # Get frontend URL
        frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
        if not frontend_url:
            frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
        
        if not frontend_url:
            frontend_url = "http://localhost:8081"
        
        test_user_id = 9000002
        
        # Construct URL with %23 encoding
        if "/api" in frontend_url or ":8055" in frontend_url:
            base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
            profile_url = f"{base_url}/%23/user/{test_user_id}"
        else:
            profile_url = f"{frontend_url}/%23/user/{test_user_id}"
        
        print(f"[DEBUG] Profile URL: {profile_url}")
        
        # Test the exact format used in match_system.py (f-string)
        formatted_link_ru = f'👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'
        formatted_link_en = f'👤 <b>View Full Profile:</b> <a href="{profile_url}">Open Profile</a>'
        
        try:
            sent1 = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text=f"Финальный тест (f-string, RU):\n\n{formatted_link_ru}",
                parse_mode="HTML"
            )
            print(f"[OK] Test 1 (RU f-string) sent! Message ID: {sent1.message_id}")
        except Exception as e:
            print(f"[ERROR] Test 1 failed: {e}")
        
        try:
            sent2 = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text=f"Final test (f-string, EN):\n\n{formatted_link_en}",
                parse_mode="HTML"
            )
            print(f"[OK] Test 2 (EN f-string) sent! Message ID: {sent2.message_id}")
        except Exception as e:
            print(f"[ERROR] Test 2 failed: {e}")
        
        # Also test with single quotes in href (alternative format)
        formatted_link_single = f"👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"
        try:
            sent3 = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text=f"Тест с одинарными кавычками:\n\n{formatted_link_single}",
                parse_mode="HTML"
            )
            print(f"[OK] Test 3 (single quotes) sent! Message ID: {sent3.message_id}")
        except Exception as e:
            print(f"[ERROR] Test 3 failed: {e}")
        
        print(f"\n[INFO] Check Telegram - see which format makes link clickable")
        print(f"[INFO] Profile URL used: {profile_url}")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
