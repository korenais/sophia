"""Test different link formats to find what works"""
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
        profile_url = "http://localhost:8081/#/user/9000001"
        
        # Test different formats
        formats = [
            # Format 1: Double quotes in f-string
            (1, f'👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'),
            # Format 2: Using format with double quotes
            (2, '👤 <b>Полный профиль:</b> <a href="{url}">Открыть профиль</a>'.format(url=profile_url)),
            # Format 3: Escaped double quotes
            (3, f'👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>'),
            # Format 4: URL without hash (test)
            (4, f'👤 <b>Полный профиль:</b> <a href="http://localhost:8081/user/9000001">Открыть профиль</a>'),
            # Format 5: URL encoded hash
            (5, f'👤 <b>Полный профиль:</b> <a href="http://localhost:8081/%23/user/9000001">Открыть профиль</a>'),
        ]
        
        for num, message_text in formats:
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Тест {num}:\n\n{message_text}",
                    parse_mode="HTML"
                )
                print(f"[OK] Test {num} sent! Message ID: {sent.message_id}")
            except Exception as e:
                print(f"[ERROR] Test {num} failed: {e}")
        
        print("\n[INFO] Check Telegram - see which format makes link clickable")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
