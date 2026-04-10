"""Check which bot is configured"""
from pathlib import Path
from dotenv import load_dotenv
import os
import asyncio
from aiogram import Bot

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
load_dotenv(env_path)

token = os.getenv('TELEGRAM_TOKEN')

if not token:
    print("ERROR: TELEGRAM_TOKEN not found in infra/.env")
    exit(1)

async def get_bot_info():
    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        print(f"Bot username: @{me.username}")
        print(f"Bot name: {me.first_name}")
        print(f"Bot ID: {me.id}")
    finally:
        await bot.session.close()

asyncio.run(get_bot_info())
