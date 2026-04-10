"""
Скрипт для создания пользователя Anton Anisimov и отправки тестовой встречи
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
import numpy as np
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@db:5432/postgres")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from db import get_pool, get_user_language
from vectorization import vectorize_description


async def create_anton_anisimov(db_pool):
    """Создать или обновить пользователя Anton Anisimov"""
    user_id = 1541686636  # Используем фиксированный ID для Anton
    telegram_username = "anton_anisim0v"
    
    # Генерируем данные для пользователя
    name = "Anton Anisimov"
    location = "Moscow, Russia"
    description = """Experienced business professional and entrepreneur with expertise in technology, 
business development, and strategic consulting. Focused on digital transformation, innovation, 
and building successful business partnerships. Strong background in software development, 
project management, and international business relations."""
    
    linkedin = "https://www.linkedin.com/in/anisimov/"
    hobbies = "Technology, business networking, innovation, strategic planning"
    skills = "Business development, strategic consulting, project management, technology leadership"
    field_of_activity = "Technology & Consulting"
    
    async with db_pool.acquire() as conn:
        # Векторизуем описание
        vector = await vectorize_description(description)
        
        # Создаем или обновляем пользователя
        await conn.execute("""
            INSERT INTO users (
                user_id, intro_name, intro_location, intro_description,
                intro_linkedin, intro_hobbies_drivers, intro_skills,
                field_of_activity, vector_description, finishedonboarding,
                state, user_telegram_link, language, matches_disabled
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, true, 'ACTIVE', $10, 'en', false)
            ON CONFLICT (user_id) DO UPDATE SET
                intro_name = EXCLUDED.intro_name,
                intro_location = EXCLUDED.intro_location,
                intro_description = EXCLUDED.intro_description,
                intro_linkedin = EXCLUDED.intro_linkedin,
                intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
                intro_skills = EXCLUDED.intro_skills,
                field_of_activity = EXCLUDED.field_of_activity,
                vector_description = EXCLUDED.vector_description,
                finishedonboarding = true,
                state = 'ACTIVE',
                user_telegram_link = EXCLUDED.user_telegram_link,
                language = EXCLUDED.language,
                matches_disabled = false,
                updated_at = NOW()
        """, 
            user_id, name, location, description, linkedin, hobbies, skills,
            field_of_activity, vector, telegram_username
        )
        
        print(f"[OK] Пользователь создан/обновлен: {name} (ID: {user_id}, @{telegram_username})")
        return user_id


async def create_test_partner(db_pool, anton_user_id):
    """Создать тестового партнера для встречи"""
    test_user_id = 999999999
    
    async with db_pool.acquire() as conn:
        # Получаем вектор Anton для создания похожего
        anton = await conn.fetchrow(
            "SELECT vector_description FROM users WHERE user_id = $1",
            anton_user_id
        )
        
        test_vector = anton['vector_description'] if anton and anton['vector_description'] else [0.1] * 3072
        
        # Создаем тестового партнера
        await conn.execute("""
            INSERT INTO users (
                user_id, intro_name, intro_location, intro_description,
                vector_description, finishedonboarding, state, matches_disabled
            ) VALUES ($1, $2, $3, $4, $5, true, 'ACTIVE', false)
            ON CONFLICT (user_id) DO UPDATE SET
                intro_name = EXCLUDED.intro_name,
                state = 'ACTIVE',
                finishedonboarding = true,
                matches_disabled = false
        """, 
            test_user_id,
            "Vladislav Redko",
            "Moscow, Russia",
            "Business development professional with expertise in technology consulting and strategic partnerships. Experienced in building business networks and facilitating professional connections.",
            test_vector
        )
        
        print(f"[OK] Тестовый партнер создан: Vladislav Redko (ID: {test_user_id})")
        return test_user_id


async def create_meeting(db_pool, user1_id, user2_id):
    """Создать встречу между двумя пользователями"""
    async with db_pool.acquire() as conn:
        # Удаляем старые встречи для чистого теста
        await conn.execute("""
            DELETE FROM meetings
            WHERE (user_1_id = $1 AND user_2_id = $2) 
               OR (user_1_id = $2 AND user_2_id = $1)
        """, user1_id, user2_id)
        
        # Создаем новую встречу
        meeting_id = await conn.fetchval("""
            INSERT INTO meetings (user_1_id, user_2_id, status)
            VALUES ($1, $2, 'new')
            RETURNING id
        """, user1_id, user2_id)
        
        print(f"[OK] Встреча создана: ID {meeting_id}")
        return meeting_id


async def send_match_notification(bot, db_pool, anton_user_id, partner_user_id, meeting_id):
    """Отправить уведомление о встрече"""
    async with db_pool.acquire() as conn:
        # Получаем информацию о партнере
        partner = await conn.fetchrow("""
            SELECT intro_name, intro_location, intro_description, 
                   intro_linkedin, user_telegram_link, intro_image
            FROM users WHERE user_id = $1
        """, partner_user_id)
        
        if not partner:
            print("[ERROR] Партнер не найден")
            return
        
        # Получаем язык пользователя
        user_lang = await get_user_language(db_pool, anton_user_id)
        
        partner_name = partner['intro_name'] or "Business Partner"
        partner_location = partner['intro_location'] or ""
        partner_description = partner['intro_description'] or ""
        partner_linkedin = partner['intro_linkedin'] or ""
        telegram_link = partner.get('user_telegram_link', '')
        
        # Формируем сообщение
        if user_lang == 'ru':
            greeting = "Успешного нетворкинга!"
            if telegram_link:
                name_display = f'<a href="https://t.me/{telegram_link.replace("@", "")}">{partner_name}</a>'
            else:
                name_display = f'<b>{partner_name}</b>'
            
            message_text = f"{greeting}\n\n"
            message_text += f"Telegram\n{name_display}\n"
            
            if partner_location:
                message_text += f"{partner_location}\n"
            if partner_description:
                message_text += f"\n{partner_description}\n"
            if partner_linkedin:
                message_text += f"\nLinkedIn: {partner_linkedin}"
            
            button_met = "Встреча состоялась"
            button_block = "Исключить контакт"
            button_disable = "Отключить рекомендации"
            button_profile = "Открыть профиль"
        else:
            greeting = "Successful networking!"
            if telegram_link:
                name_display = f'<a href="https://t.me/{telegram_link.replace("@", "")}">{partner_name}</a>'
            else:
                name_display = f'<b>{partner_name}</b>'
            
            message_text = f"{greeting}\n\n"
            message_text += f"Telegram\n{name_display}\n"
            
            if partner_location:
                message_text += f"{partner_location}\n"
            if partner_description:
                message_text += f"\n{partner_description}\n"
            if partner_linkedin:
                message_text += f"\nLinkedIn: {partner_linkedin}"
            
            button_met = "Meeting completed"
            button_block = "Exclude contact"
            button_disable = "Disable recommendations"
            button_profile = "Open profile"
        
        # Создаем кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=button_profile, 
                                   callback_data=f"match_view_{meeting_id}")
            ],
            [
                InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}")
            ],
            [
                InlineKeyboardButton(text=button_block, 
                                   callback_data=f"match_block_{meeting_id}_{partner_user_id}")
            ],
            [
                InlineKeyboardButton(text=button_disable, 
                                   callback_data=f"match_disable_{meeting_id}")
            ]
        ])
        
        try:
            # Отправляем фото, если есть
            if partner.get('intro_image'):
                try:
                    import base64
                    photo_data = base64.b64decode(partner['intro_image'])
                    from io import BytesIO
                    photo_file = BytesIO(photo_data)
                    photo_file.name = "profile.jpg"
                    
                    if telegram_link:
                        photo_caption = f"<a href=\"https://t.me/{telegram_link.replace('@', '')}\">{partner_name}</a>"
                    else:
                        photo_caption = partner_name
                    
                    await bot.send_photo(anton_user_id, photo_file, caption=photo_caption, 
                                       parse_mode="HTML", reply_markup=keyboard)
                    print(f"[OK] Уведомление с фото отправлено пользователю {anton_user_id}")
                    return
                except Exception as e:
                    print(f"[WARNING] Не удалось отправить фото: {e}, отправляем текстовое сообщение")
            
            # Отправляем текстовое сообщение
            await bot.send_message(anton_user_id, message_text, parse_mode="HTML", 
                                 reply_markup=keyboard)
            print(f"[OK] Уведомление отправлено пользователю {anton_user_id}")
            
        except Exception as e:
            print(f"[ERROR] Ошибка при отправке уведомления: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Основная функция"""
    print("=" * 70)
    print("Создание пользователя Anton Anisimov и тестовой встречи")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN не установлен")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Шаг 1: Создать пользователя Anton Anisimov
        print("\n[ШАГ 1] Создание пользователя Anton Anisimov...")
        anton_user_id = await create_anton_anisimov(db_pool)
        
        # Шаг 2: Создать тестового партнера
        print("\n[ШАГ 2] Создание тестового партнера...")
        partner_user_id = await create_test_partner(db_pool, anton_user_id)
        
        # Шаг 3: Создать встречу
        print("\n[ШАГ 3] Создание встречи...")
        meeting_id = await create_meeting(db_pool, anton_user_id, partner_user_id)
        
        # Шаг 4: Отправить уведомление
        print("\n[ШАГ 4] Отправка уведомления...")
        await send_match_notification(bot, db_pool, anton_user_id, partner_user_id, meeting_id)
        
        print("\n" + "=" * 70)
        print("[SUCCESS] Пользователь создан и встреча отправлена!")
        print(f"   Anton Anisimov ID: {anton_user_id}")
        print(f"   Partner ID: {partner_user_id}")
        print(f"   Meeting ID: {meeting_id}")
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

