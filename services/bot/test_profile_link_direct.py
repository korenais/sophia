"""Test profile link directly"""
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
            # Format 1: Direct double quotes
            f'👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>',
            # Format 2: Using format method
            '👤 <b>Полный профиль:</b> <a href="{url}">Открыть профиль</a>'.format(url=profile_url),
        ]
        
        for i, message_text in enumerate(formats, 1):
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Тест {i}:\n\n{message_text}",
                    parse_mode="HTML"
                )
                print(f"[OK] Test {i} sent! Message ID: {sent.message_id}")
                print(f"Format: {i}")
            except Exception as e:
                print(f"[ERROR] Test {i} failed: {e}")
        
        print("\n[INFO] Check Telegram - profile links should be clickable")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
