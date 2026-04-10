"""Debug why links are not clickable"""
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
        # Test different URL formats
        test_urls = [
            # Test 1: localhost with %23
            ("http://localhost:8081/%23/user/9000002", "localhost with %23"),
            # Test 2: localhost with # (not encoded)
            ("http://localhost:8081/#/user/9000002", "localhost with #"),
            # Test 3: Public URL format (example)
            ("https://example.com/user/9000002", "public URL"),
            # Test 4: Simple HTTP URL
            ("http://example.com/user/9000002", "simple HTTP URL"),
        ]
        
        for url, description in test_urls:
            # Test with double quotes
            link_double = f'👤 <b>Полный профиль:</b> <a href="{url}">Открыть профиль</a>'
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Test: {description}\nDouble quotes:\n{link_double}",
                    parse_mode="HTML"
                )
                print(f"[OK] {description} (double quotes) sent! Message ID: {sent.message_id}")
            except Exception as e:
                print(f"[ERROR] {description} (double quotes) failed: {e}")
            
            # Test with single quotes
            link_single = f"👤 <b>Полный профиль:</b> <a href='{url}'>Открыть профиль</a>"
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Test: {description}\nSingle quotes:\n{link_single}",
                    parse_mode="HTML"
                )
                print(f"[OK] {description} (single quotes) sent! Message ID: {sent.message_id}")
            except Exception as e:
                print(f"[ERROR] {description} (single quotes) failed: {e}")
            
            # Test simple link without emoji and bold
            link_simple = f'<a href="{url}">Открыть профиль</a>'
            try:
                sent = await bot.send_message(
                    chat_id=ANTON_USER_ID,
                    text=f"Test: {description}\nSimple link:\n{link_simple}",
                    parse_mode="HTML"
                )
                print(f"[OK] {description} (simple) sent! Message ID: {sent.message_id}")
            except Exception as e:
                print(f"[ERROR] {description} (simple) failed: {e}")
        
        # Test with Markdown format
        try:
            sent = await bot.send_message(
                chat_id=ANTON_USER_ID,
                text="Test Markdown:\n[Open Profile](http://example.com/user/9000002)",
                parse_mode="Markdown"
            )
            print(f"[OK] Markdown format sent! Message ID: {sent.message_id}")
        except Exception as e:
            print(f"[ERROR] Markdown format failed: {e}")
        
        print(f"\n[INFO] Check Telegram - see which format makes link clickable")
        print(f"[WARNING] Telegram may not make localhost URLs clickable for security reasons")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test())
