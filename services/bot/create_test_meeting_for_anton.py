"""
Скрипт для создания тестовой встречи для Anton Anisimov (@anton_anisim0v)
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncpg
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


async def find_user_by_telegram_username(db_pool, username):
    """Найти пользователя по Telegram username"""
    username_clean = username.replace('@', '')
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, state, finishedonboarding, 
                   vector_description, user_telegram_link
            FROM public.users
            WHERE user_telegram_link = $1 OR user_telegram_link = $2
            LIMIT 1
            """,
            username_clean,
            f"@{username_clean}"
        )
        return dict(row) if row else None


async def find_or_create_test_partner(db_pool, anton_user_id):
    """Найти или создать тестового партнера"""
    test_user_id = 999999999  # Используем высокий ID для тестового пользователя
    
    async with db_pool.acquire() as conn:
        # Проверяем, существует ли уже тестовый пользователь
        existing = await conn.fetchrow(
            "SELECT user_id, intro_name FROM users WHERE user_id = $1",
            test_user_id
        )
        
        if existing:
            print(f"[INFO] Тестовый пользователь уже существует: {existing['intro_name']}")
            return test_user_id
        
        # Получаем вектор Anton для создания похожего вектора
        anton = await conn.fetchrow(
            "SELECT vector_description FROM users WHERE user_id = $1",
            anton_user_id
        )
        
        test_vector = anton['vector_description'] if anton and anton['vector_description'] else [0.1] * 3072
        
        # Создаем тестового пользователя
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
            "Test Partner Vladislav",
            "Moscow, Russia",
            "Test business partner for meeting verification. Experienced professional in technology and business development.",
            test_vector
        )
        
        print(f"[OK] Создан тестовый пользователь: Test Partner Vladislav (ID: {test_user_id})")
        return test_user_id


async def create_meeting(db_pool, user1_id, user2_id):
    """Создать встречу между двумя пользователями"""
    async with db_pool.acquire() as conn:
        # Проверяем, нет ли уже встречи
        existing = await conn.fetchrow("""
            SELECT id, status FROM meetings
            WHERE (user_1_id = $1 AND user_2_id = $2) 
               OR (user_1_id = $2 AND user_2_id = $1)
            ORDER BY created_at DESC LIMIT 1
        """, user1_id, user2_id)
        
        if existing:
            print(f"[INFO] Встреча уже существует: ID {existing['id']}, статус: {existing['status']}")
            return existing['id']
        
        # Создаем новую встречу
        meeting_id = await conn.fetchval("""
            INSERT INTO meetings (user_1_id, user_2_id, status)
            VALUES ($1, $2, 'new')
            RETURNING id
        """, user1_id, user2_id)
        
        print(f"[OK] Создана встреча: ID {meeting_id}")
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
            greeting = "🎯 Успешного нетворкинга!"
            if telegram_link:
                name_display = f'<a href="https://t.me/{telegram_link.replace("@", "")}">{partner_name}</a>'
            else:
                name_display = f'<b>{partner_name}</b>'
            
            message_text = f"{greeting} 🚀\n\n"
            message_text += f"Telegram\n{name_display}\n"
            
            if partner_location:
                message_text += f"📍 {partner_location}\n"
            if partner_description:
                message_text += f"\n{partner_description}\n"
            if partner_linkedin:
                message_text += f"\n🔗 LinkedIn: {partner_linkedin}"
            
            button_met = "✅ Встреча состоялась"
            button_block = "🚫 Исключить контакт"
            button_disable = "⛔ Отключить рекомендации"
        else:
            greeting = "🎯 Successful networking!"
            if telegram_link:
                name_display = f'<a href="https://t.me/{telegram_link.replace("@", "")}">{partner_name}</a>'
            else:
                name_display = f'<b>{partner_name}</b>'
            
            message_text = f"{greeting} 🚀\n\n"
            message_text += f"Telegram\n{name_display}\n"
            
            if partner_location:
                message_text += f"📍 {partner_location}\n"
            if partner_description:
                message_text += f"\n{partner_description}\n"
            if partner_linkedin:
                message_text += f"\n🔗 LinkedIn: {partner_linkedin}"
            
            button_met = "✅ Meeting completed"
            button_block = "🚫 Exclude contact"
            button_disable = "⛔ Disable recommendations"
        
        # Создаем кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Открыть профиль" if user_lang == 'ru' else "👤 Open profile", 
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
                        photo_caption = f"📸 <a href=\"https://t.me/{telegram_link.replace('@', '')}\">{partner_name}</a>"
                    else:
                        photo_caption = f"📸 {partner_name}"
                    
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


async def main():
    """Основная функция"""
    print("=" * 70)
    print("Создание тестовой встречи для Anton Anisimov (@anton_anisim0v)")
    print("=" * 70)
    
    if not TELEGRAM_TOKEN:
        print("[ERROR] TELEGRAM_TOKEN не установлен")
        return
    
    db_pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=3)
    bot = Bot(token=TELEGRAM_TOKEN)
    
    try:
        # Шаг 1: Найти Anton Anisimov
        print("\n[ШАГ 1] Поиск пользователя @anton_anisim0v...")
        anton = await find_user_by_telegram_username(db_pool, "anton_anisim0v")
        
        if not anton:
            print("[ERROR] Пользователь @anton_anisim0v не найден в базе данных!")
            print("   Убедитесь, что пользователь зарегистрирован в боте (/start)")
            return
        
        anton_user_id = anton['user_id']
        print(f"[OK] Найден пользователь: {anton.get('intro_name', 'Unknown')} (ID: {anton_user_id})")
        print(f"   Статус: {anton.get('state', 'UNKNOWN')}")
        print(f"   Завершен онбординг: {anton.get('finishedonboarding', False)}")
        
        # Убеждаемся, что пользователь активен
        if anton.get('state') != 'ACTIVE':
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET state = 'ACTIVE' WHERE user_id = $1",
                    anton_user_id
                )
            print("[OK] Статус пользователя обновлен на ACTIVE")
        
        if not anton.get('finishedonboarding'):
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET finishedonboarding = true WHERE user_id = $1",
                    anton_user_id
                )
            print("[OK] finishedonboarding установлен в true")
        
        # Шаг 2: Найти или создать тестового партнера
        print("\n[ШАГ 2] Поиск/создание тестового партнера...")
        partner_user_id = await find_or_create_test_partner(db_pool, anton_user_id)
        
        # Шаг 3: Создать встречу
        print("\n[ШАГ 3] Создание встречи...")
        meeting_id = await create_meeting(db_pool, anton_user_id, partner_user_id)
        
        # Шаг 4: Отправить уведомление
        print("\n[ШАГ 4] Отправка уведомления...")
        await send_match_notification(bot, db_pool, anton_user_id, partner_user_id, meeting_id)
        
        print("\n" + "=" * 70)
        print("[SUCCESS] Тестовая встреча создана и уведомление отправлено!")
        print(f"   Meeting ID: {meeting_id}")
        print(f"   Партнер ID: {partner_user_id}")
        print("=" * 70)
        print("\nТеперь вы можете:")
        print("1. Проверить Telegram бота - должно прийти уведомление")
        print("2. Нажать кнопку 'Встреча состоялась'")
        print("3. После этого запустить генерацию новых матчей")
        print("4. Проверить, появится ли тот же партнер снова")
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

