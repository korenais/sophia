"""Test profile link formatting to ensure it's clickable"""
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
        
        # Test different HTML formats
        formats = [
            # Format 1: Using double quotes in href (standard)
            (1, f'👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'),
            # Format 2: Using single quotes in href
            (2, f"👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"),
            # Format 3: Using format() method like in match_system.py
            (3, '👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'.format(profile_url=profile_url)),
            # Format 4: URL without encoding (should fail, but test)
            (4, f'👤 <b>Полный профиль:</b> <a href="{profile_url.replace("%23", "#")}">Открыть профиль</a>'),
            # Format 5: Simple test link
            (5, f'<a href="{profile_url}">Открыть профиль</a>'),
        ]
        
        for num, message_text in formats:
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Тест ссылки {num}:\n\n{message_text}",
                    parse_mode="HTML"
                )
                print(f"[OK] Test {num} sent! Message ID: {sent.message_id}")
            except Exception as e:
                print(f"[ERROR] Test {num} failed: {e}")
        
        # Also test the exact format from scenes.py
        profile_link_template = '👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'
        formatted_link = profile_link_template.format(profile_url=profile_url)
        try:
            sent = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text=f"Тест точного формата из scenes.py:\n\n{formatted_link}",
                parse_mode="HTML"
            )
            print(f"[OK] Exact format test sent! Message ID: {sent.message_id}")
        except Exception as e:
            print(f"[ERROR] Exact format test failed: {e}")
        
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
