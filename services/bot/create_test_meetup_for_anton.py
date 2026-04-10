"""
Скрипт для создания тестовой рекомендации (meetup) для пользователя Anton Anisimov
с новым сгенерированным контактом
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
import numpy as np
from datetime import datetime

# Load environment
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@db:5432/postgres")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from db import get_pool, create_meetings, get_user_info, get_user_language
from match_system import MatchSystem
from vectorization import openai_text_to_vector, create_default_vector
from aiogram import Bot

ANTON_USER_ID = 1541686636  # Anton Anisimov
ANTON_USERNAME = "anton_anisim0v"

# Генерируем уникальный ID для нового тестового пользователя
# Используем timestamp для уникальности
import time
NEW_PARTNER_ID = int(time.time()) % 1000000000  # Ограничиваем до 9 цифр


async def check_anton_exists(db_pool):
    """Проверить существование пользователя Anton Anisimov"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, intro_name, finishedonboarding, state FROM users WHERE user_id = $1",
            ANTON_USER_ID
        )
        if user:
            print(f"[OK] Пользователь найден: {user['intro_name']} (ID: {ANTON_USER_ID})")
            print(f"   finishedonboarding: {user['finishedonboarding']}, state: {user['state']}")
            return True
        else:
            print(f"[ERROR] Пользователь Anton Anisimov (ID: {ANTON_USER_ID}) не найден в базе данных!")
            return False


async def create_new_test_partner(db_pool, openai_client):
    """Создать нового тестового партнера для встречи"""
    print(f"\n[ШАГ 1] Создание нового тестового партнера (ID: {NEW_PARTNER_ID})...")
    
    # Генерируем уникальные данные для нового партнера
    partner_name = f"Test Partner {datetime.now().strftime('%H%M%S')}"
    partner_location = "Tallinn, Estonia"
    partner_description = """Experienced technology consultant and business strategist with expertise in 
digital transformation, innovation management, and cross-border business development. 
Passionate about connecting professionals and facilitating meaningful business relationships. 
Strong background in fintech, SaaS solutions, and international market expansion."""
    
    # Векторизуем описание
    partner_vector = None
    if openai_client:
        try:
            partner_vector = await openai_text_to_vector(partner_description, openai_client=openai_client)
            print("[OK] Вектор создан через OpenAI")
        except Exception as e:
            print(f"[WARNING] Ошибка при создании вектора через OpenAI: {e}")
    
    if partner_vector is None:
        print("[INFO] Используем дефолтный вектор")
        partner_vector = await create_default_vector(openai_client=openai_client)
        if partner_vector is None:
            # Создаем простой вектор вручную
            partner_vector = [0.1 + (NEW_PARTNER_ID % 10) * 0.01] * 3072
            print("[INFO] Создан простой вектор вручную")
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (
                user_id, chat_id, intro_name, intro_location, intro_description,
                vector_description, finishedonboarding, state, language,
                user_telegram_link, matches_disabled
            ) VALUES ($1, $2, $3, $4, $5, $6, true, 'ACTIVE', 'en', $7, false)
            ON CONFLICT (user_id) DO UPDATE SET
                intro_name = EXCLUDED.intro_name,
                intro_location = EXCLUDED.intro_location,
                intro_description = EXCLUDED.intro_description,
                vector_description = EXCLUDED.vector_description,
                finishedonboarding = true,
                state = 'ACTIVE',
                matches_disabled = false,
                updated_at = NOW()
        """, 
            NEW_PARTNER_ID,
            NEW_PARTNER_ID,  # chat_id = user_id для приватного чата
            partner_name,
            partner_location,
            partner_description,
            partner_vector,
            f"test_partner_{NEW_PARTNER_ID}"  # user_telegram_link
        )
        
        print(f"[OK] Тестовый партнер создан:")
        print(f"   Имя: {partner_name}")
        print(f"   ID: {NEW_PARTNER_ID}")
        print(f"   Локация: {partner_location}")
        
        return NEW_PARTNER_ID


async def create_and_send_meetup(db_pool, bot, anton_user_id, partner_user_id):
    """Создать встречу и отправить уведомление"""
    print(f"\n[ШАГ 2] Создание встречи между {anton_user_id} и {partner_user_id}...")
    
    # Создаем встречу
    meeting_ids = await create_meetings(db_pool, [(anton_user_id, partner_user_id)])
    meeting_id = meeting_ids[0]
    print(f"[OK] Встреча создана: ID {meeting_id}")
    
    # Отправляем уведомление через MatchSystem
    print(f"\n[ШАГ 3] Отправка уведомления через MatchSystem...")
    match_system = MatchSystem(bot, db_pool)
    
    # Используем notify_matches для отправки уведомления
    pairs_with_ids = [(anton_user_id, partner_user_id, meeting_id)]
    await match_system.notify_matches(pairs_with_ids)
    
    print(f"[OK] Уведомление отправлено пользователю {anton_user_id}")
    
    return meeting_id


async def main():
    """Основная функция"""
    print("=" * 70)
    print("Создание тестовой рекомендации для Anton Anisimov")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN не установлен. Уведомления не будут отправлены.")
        return
    
    db_pool = await get_pool(DB_URL)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    # Инициализируем OpenAI клиент, если доступен
    openai_client = None
    if OPENAI_API_KEY:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("[INFO] OpenAI клиент инициализирован")
    else:
        print("[WARNING] OPENAI_API_KEY не установлен, будут использованы дефолтные векторы")
    
    try:
        # Проверяем существование Anton
        if not await check_anton_exists(db_pool):
            print("\n[ERROR] Пользователь Anton Anisimov не найден!")
            print("   Запустите сначала create_anton_and_meetup.py для создания пользователя")
            return
        
        # Создаем нового тестового партнера
        partner_user_id = await create_new_test_partner(db_pool, openai_client)
        
        # Создаем встречу и отправляем уведомление
        meeting_id = await create_and_send_meetup(db_pool, bot, ANTON_USER_ID, partner_user_id)
        
        print("\n" + "=" * 70)
        print("[SUCCESS] Тестовая рекомендация создана и отправлена!")
        print(f"   Anton Anisimov ID: {ANTON_USER_ID}")
        print(f"   Новый партнер ID: {partner_user_id}")
        print(f"   Meeting ID: {meeting_id}")
        print("=" * 70)
        print(f"\nПользователь @{ANTON_USERNAME} должен получить уведомление в Telegram")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] Произошла ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

