from __future__ import annotations

import asyncio
import asyncpg
import os
from datetime import datetime, date
import logging
from aiogram import Bot
from typing import List, Dict, Any, Optional
from scenes import BOT_MESSAGES, get_messages
from db import get_user_info

logger = logging.getLogger(__name__)

# Telegram message maximum length
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

def is_birthday_functionality_enabled() -> bool:
    """Check if birthday functionality is enabled via environment variable"""
    birthdays_enabled = os.getenv("BIRTHDAYS", "No").strip().lower()
    return birthdays_enabled in ("yes", "true", "1", "on", "enabled")


async def translate_name(name: str, target_language: str, openai_client=None) -> str:
    """
    Translate name to target language (ru or en) using OpenAI for transliteration.
    If OpenAI is unavailable or translation fails, returns original name.
    If name is in other languages (Arabic, Hebrew, etc.), returns original.
    
    Args:
        name: Name to translate
        target_language: Target language ('ru' or 'en')
        openai_client: Optional OpenAI client instance
    
    Returns:
        Translated name or original if translation not applicable/failed
    """
    if not name:
        return name
    
    # Check if name contains Arabic/Hebrew characters - don't translate these
    has_arabic_hebrew = any(
        '\u0600' <= char <= '\u06FF' or  # Arabic
        '\u0590' <= char <= '\u05FF'     # Hebrew
        for char in name
    )
    
    if has_arabic_hebrew:
        return name
    
    # Check if name contains Cyrillic characters
    has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in name)
    
    # If target is Russian and name already has Cyrillic, return as is
    if target_language.lower() == 'ru' and has_cyrillic:
        return name
    
    # If target is English and name has no Cyrillic, return as is
    if target_language.lower() == 'en' and not has_cyrillic:
        return name
    
    # Try to translate using OpenAI if available
    if openai_client:
        try:
            if target_language.lower() == 'ru':
                prompt = f"Transliterate this name from English/Latin to Russian Cyrillic. Return only the transliterated name, nothing else. Name: {name}"
            else:
                prompt = f"Transliterate this name from Russian Cyrillic to English/Latin. Return only the transliterated name, nothing else. Name: {name}"
            
            completion = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a name transliteration assistant. Return only the transliterated name, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            translated = completion.choices[0].message.content.strip()
            
            # Validate translation - should not be empty and should be different from original
            if translated and translated != name:
                # Basic validation: if target is Russian, should contain Cyrillic
                if target_language.lower() == 'ru':
                    if any('\u0400' <= char <= '\u04FF' for char in translated):
                        return translated
                # If target is English, should not contain Cyrillic
                else:
                    if not any('\u0400' <= char <= '\u04FF' for char in translated):
                        return translated
            
            # If translation is invalid, fall through to return original
            logger.debug(f"OpenAI translation returned invalid result for '{name}', using original")
        except Exception as e:
            logger.debug(f"Error translating name '{name}' with OpenAI: {e}, using original")
    
    # Fallback: return original name if translation failed or OpenAI unavailable
    return name


async def generate_personalized_greeting(
    name: str,
    description: Optional[str] = None,
    hobbies: Optional[str] = None,
    field_of_activity: Optional[str] = None,
    language: str = "ru",
    openai_client=None,
    standard_greeting: str = None
) -> str:
    """
    Generate personalized birthday greeting using OpenAI.
    
    Args:
        name: User's name (already translated)
        description: User's description
        hobbies: User's hobbies and drivers
        field_of_activity: User's field of activity
        language: Language for greeting ('ru' or 'en')
        openai_client: OpenAI client instance
        standard_greeting: Standard greeting to use as fallback/base
    
    Returns:
        Generated greeting message (max 4096 chars)
    """
    # If no description or empty description, use standard greeting (don't generate personalized)
    if not description or not description.strip():
        return standard_greeting or ""
    
    # If no OpenAI client, use standard greeting
    if not openai_client:
        return standard_greeting or ""
    
    # Build user context
    user_context = []
    if description:
        user_context.append(f"Description: {description}")
    if hobbies:
        user_context.append(f"Hobbies & Drivers: {hobbies}")
    if field_of_activity:
        user_context.append(f"Field of Activity: {field_of_activity}")
    
    context_text = "\n".join(user_context) if user_context else "No additional information available."
    
    # Determine language for prompt
    if language.lower() == "ru":
        system_prompt = """Ты помощник для генерации поздравительных сообщений для бизнес-клуба.
Создай дружелюбное, но лаконичное поздравление с днем рождения в деловом стиле.
Поздравление должно быть профессиональным, но теплым, подходящим для бизнес-аудитории.
Используй информацию о пользователе для персонализации, но не перегружай деталями.
Максимальная длина: 300 слов."""
        user_prompt = f"""Создай персонализированное поздравление с днем рождения для {name}.

Информация о пользователе:
{context_text}

Используй стандартное поздравление как основу:
{standard_greeting or 'С Днём Рождения!'}

Создай дружелюбное, но лаконичное поздравление в деловом стиле для бизнес-клуба."""
    else:
        system_prompt = """You are an assistant for generating birthday greetings for a business club.
Create a friendly but concise birthday greeting in a business style.
The greeting should be professional but warm, suitable for a business audience.
Use user information for personalization, but don't overload with details.
Maximum length: 300 words."""
        user_prompt = f"""Create a personalized birthday greeting for {name}.

User information:
{context_text}

Use the standard greeting as a base:
{standard_greeting or 'Happy Birthday!'}

Create a friendly but concise greeting in business style for a business club."""
    
    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        generated_text = completion.choices[0].message.content or ""
        
        # Ensure message doesn't exceed Telegram limit
        if len(generated_text) > TELEGRAM_MAX_MESSAGE_LENGTH:
            generated_text = generated_text[:TELEGRAM_MAX_MESSAGE_LENGTH - 3] + "..."
        
        return generated_text.strip()
        
    except Exception as e:
        logger.error(f"Error generating personalized greeting with OpenAI: {e}")
        # Return standard greeting on error
        return standard_greeting or ""


async def send_birthday_greeting(
    bot: Bot, 
    user_id: int, 
    user_name: str, 
    db_pool=None, 
    force_send: bool = False,
    openai_client=None
) -> bool:
    """Send birthday greeting to birthday topic
    
    Args:
        bot: Bot instance
        user_id: User ID
        user_name: User name
        db_pool: Database pool
        force_send: If True, send even if already sent today (for immediate checks)
        openai_client: Optional OpenAI client for personalized greetings
    """
    try:
        today = date.today()
        
        # Check if we've already sent today (unless forced)
        if db_pool and not force_send:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT last_birthday_greeting_sent FROM users WHERE user_id = $1",
                    user_id
                )
                if row and row['last_birthday_greeting_sent'] == today:
                    logger.info(f"Birthday greeting already sent today for user {user_id}, skipping")
                    return False
        
        # Get birthday topic ID from environment
        birthday_topic_id = os.getenv("BIRTHDAY_TOPIC_ID")
        if not birthday_topic_id:
            error_msg = "BIRTHDAY_TOPIC_ID not set, cannot send birthday greeting"
            logger.error(error_msg)
            # Create bug report if db_pool is available
            if db_pool:
                try:
                    from bug_reporting import report_bug
                    await report_bug(
                        error_type="birthday_greeting",
                        error_message=error_msg,
                        context={
                            "user_id": user_id,
                            "user_name": user_name,
                            "missing_config": "BIRTHDAY_TOPIC_ID"
                        },
                        severity="high"
                    )
                except Exception as br_e:
                    logger.warning(f"Could not create bug report: {br_e}")
            return False
        
        # Get group chat ID from environment
        group_chat_id = os.getenv("TELEGRAM_GROUP_ID")
        if not group_chat_id:
            error_msg = "TELEGRAM_GROUP_ID not set, cannot send birthday greeting"
            logger.error(error_msg)
            # Create bug report if db_pool is available
            if db_pool:
                try:
                    from bug_reporting import report_bug
                    await report_bug(
                        error_type="birthday_greeting",
                        error_message=error_msg,
                        context={
                            "user_id": user_id,
                            "user_name": user_name,
                            "missing_config": "TELEGRAM_GROUP_ID"
                        },
                        severity="high"
                    )
                except Exception as br_e:
                    logger.warning(f"Could not create bug report: {br_e}")
            return False
        
        # Get bot language
        bot_language = os.getenv("BOT_LANGUAGE", "ru").lower()
        
        # Get user info for personalized greeting
        user_info = None
        if db_pool:
            try:
                user_info = await get_user_info(db_pool, user_id)
            except Exception as e:
                logger.warning(f"Could not fetch user info for user {user_id}: {e}")
        
        # Translate name based on bot language
        # Try to get OpenAI client for name translation if not provided
        name_translation_client = openai_client
        if not name_translation_client:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                try:
                    from openai import AsyncOpenAI
                    name_translation_client = AsyncOpenAI(api_key=openai_api_key)
                except Exception as e:
                    logger.debug(f"Could not create OpenAI client for name translation: {e}")
        
        translated_name = await translate_name(user_name, bot_language, name_translation_client)
        
        # Get standard messages
        messages = get_messages()
        standard_greeting = messages["BIRTHDAY"]["GREETING"].format(name=translated_name)
        celebration_message = messages["BIRTHDAY"]["CELEBRATION"]
        
        # Generate personalized greeting if possible
        greeting_message = standard_greeting
        openai_error_occurred = False
        
        # Try to generate personalized greeting if we have description and OpenAI
        if user_info and user_info.get('intro_description'):
            # Create OpenAI client if not provided
            current_openai_client = openai_client
            if not current_openai_client:
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    try:
                        from openai import AsyncOpenAI
                        current_openai_client = AsyncOpenAI(api_key=openai_api_key)
                    except Exception as e:
                        logger.warning(f"Could not create OpenAI client: {e}")
            
            if current_openai_client:
                try:
                    personalized_greeting = await generate_personalized_greeting(
                        name=translated_name,
                        description=user_info.get('intro_description'),
                        hobbies=user_info.get('intro_hobbies_drivers'),
                        field_of_activity=user_info.get('field_of_activity'),
                        language=bot_language,
                        openai_client=current_openai_client,
                        standard_greeting=standard_greeting
                    )
                    
                    if personalized_greeting and personalized_greeting != standard_greeting:
                        greeting_message = personalized_greeting
                        logger.info(f"Generated personalized greeting for user {user_id}")
                    else:
                        logger.info(f"Using standard greeting for user {user_id} (generated greeting was empty or same)")
                        
                except Exception as e:
                    openai_error_occurred = True
                    error_type = type(e).__name__
                    error_str = str(e).lower()
                    
                    # Check for specific OpenAI errors that should be reported
                    is_openai_unavailable = (
                        "api key" in error_str or
                        "authentication" in error_str or
                        "invalid" in error_str and "key" in error_str or
                        "insufficient_quota" in error_str or
                        "quota" in error_str or
                        "account" in error_str and ("disabled" in error_str or "suspended" in error_str) or
                        "rate limit" in error_str
                    )
                    
                    if is_openai_unavailable and db_pool:
                        try:
                            from bug_reporting import report_bug
                            await report_bug(
                                error_type="birthday_greeting_openai",
                                error_message=f"OpenAI API error during birthday greeting generation: {error_type}: {e}",
                                context={
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "error_type": error_type,
                                    "error_details": str(e)[:500]
                                },
                                exception=e,
                                severity="high"
                            )
                            logger.info(f"Reported OpenAI error to bug reports for user {user_id}")
                        except Exception as br_e:
                            logger.warning(f"Could not create bug report for OpenAI error: {br_e}")
                    
                    logger.warning(f"Error generating personalized greeting for user {user_id}, using standard: {e}")
                    # Continue with standard greeting
            else:
                # OpenAI client not available
                if db_pool:
                    try:
                        from bug_reporting import report_bug
                        await report_bug(
                            error_type="birthday_greeting_openai",
                            error_message="OPENAI_API_KEY not available for birthday greeting generation",
                            context={
                                "user_id": user_id,
                                "user_name": user_name,
                                "missing_config": "OPENAI_API_KEY"
                            },
                            severity="high"
                        )
                        logger.info(f"Reported missing OpenAI API key to bug reports for user {user_id}")
                    except Exception as br_e:
                        logger.warning(f"Could not create bug report: {br_e}")
        
        # Build full message
        full_message = f"{celebration_message}\n\n{greeting_message}"
        
        # Ensure message doesn't exceed Telegram limit
        if len(full_message) > TELEGRAM_MAX_MESSAGE_LENGTH:
            # Truncate greeting message if needed
            max_greeting_length = TELEGRAM_MAX_MESSAGE_LENGTH - len(celebration_message) - 3  # -3 for "\n\n"
            greeting_message = greeting_message[:max_greeting_length - 3] + "..."
            full_message = f"{celebration_message}\n\n{greeting_message}"
            logger.warning(f"Truncated birthday greeting for user {user_id} to fit Telegram limit")
        
        # Send to birthday topic in the group
        await bot.send_message(
            chat_id=int(group_chat_id),
            text=full_message,
            message_thread_id=int(birthday_topic_id)
        )
        
        # Update last_birthday_greeting_sent date (always update to prevent duplicate sends)
        # This ensures that even if force_send=True was used, we mark it as sent to avoid spam
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET last_birthday_greeting_sent = $1 WHERE user_id = $2",
                    today, user_id
                )
                logger.info(f"Updated last_birthday_greeting_sent for user {user_id} to {today} (force_send={force_send})")
        
        logger.info(f"Birthday greeting sent to birthday topic for user {user_id} ({translated_name})")
        return True
    except Exception as e:
        logger.error(f"EXCEPTION CAUGHT in send_birthday_greeting: {type(e).__name__}: {e}")
        error_msg = f"Failed to send birthday greeting to birthday topic for user {user_id}: {e}"
        logger.error(error_msg)
        logger.error(f"DEBUG: db_pool value: {db_pool}, type: {type(db_pool)}")  # Use ERROR level to ensure it's shown
        
        # Create bug report for sending failures (only for critical errors)
        if db_pool:
            logger.info(f"DEBUG: db_pool is not None, attempting to create bug report")
            try:
                from bug_reporting import report_bug
                # Check if this is a critical configuration error
                is_critical = (
                    "BIRTHDAY_TOPIC_ID" in str(e) or 
                    "TELEGRAM_GROUP_ID" in str(e) or
                    "thread not found" in str(e).lower() or
                    "chat not found" in str(e).lower()
                )
                severity = "critical" if is_critical else "high"
                logger.info(f"Attempting to create bug report: type=birthday_greeting, severity={severity}, error={str(e)[:100]}")
                
                report_id = await report_bug(
                    error_type="birthday_greeting",
                    error_message=error_msg,
                    context={
                        "user_id": user_id,
                        "user_name": user_name,
                        "group_chat_id": group_chat_id if 'group_chat_id' in locals() else None,
                        "birthday_topic_id": birthday_topic_id if 'birthday_topic_id' in locals() else None,
                        "error_type": type(e).__name__
                    },
                    exception=e,
                    severity=severity
                )
                
                if report_id:
                    logger.info(f"Bug report created successfully with ID: {report_id}")
                else:
                    logger.info(f"Bug report was not created (duplicate or severity too low)")
            except Exception as br_e:
                logger.error(f"Could not create bug report: {br_e}", exc_info=True)
        else:
            logger.warning("db_pool is None, cannot create bug report")
        
        return False


async def check_birthday_for_user(bot: Bot, pool: asyncpg.pool.Pool, user_id: int) -> bool:
    """Check if a specific user has birthday today and send greeting immediately"""
    try:
        if not is_birthday_functionality_enabled():
            logger.debug("Birthday functionality is disabled, skipping immediate check")
            return False
        
        today = date.today()
        async with pool.acquire() as conn:
            # Get user info
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, intro_birthday 
                FROM users 
                WHERE user_id = $1
                AND finishedonboarding = true 
                AND intro_birthday IS NOT NULL
                AND EXTRACT(MONTH FROM intro_birthday) = $2
                AND EXTRACT(DAY FROM intro_birthday) = $3
                """,
                user_id,
                today.month,
                today.day
            )
            
            if row:
                user_name = row['intro_name'] or "there"
                logger.info(f"User {user_id} has birthday today ({row['intro_birthday']}), sending immediate greeting (force_send=True)")
                # Force send even if already sent today (for newly added/changed birthdays)
                # Note: send_birthday_greeting will update last_birthday_greeting_sent after sending to prevent spam
                success = await send_birthday_greeting(bot, user_id, user_name, pool, force_send=True)
                if success:
                    logger.info(f"Immediate birthday greeting sent successfully for user {user_id}, flag updated to prevent duplicates")
                return success
            else:
                logger.debug(f"User {user_id} does not have birthday today, no greeting needed")
                return False
    except Exception as e:
        logger.error(f"Error in check_birthday_for_user for user {user_id}: {e}")
        return False


async def check_recently_updated_birthday_greetings(bot: Bot, pool: asyncpg.pool.Pool) -> None:
    """Check for users whose birthday was recently updated (last_birthday_greeting_sent = NULL)
    and send greeting immediately. This handles admin panel updates.
    """
    # Check if birthday functionality is enabled
    if not is_birthday_functionality_enabled():
        return
    
    try:
        today = date.today()
        async with pool.acquire() as conn:
            recently_updated_birthdays = await conn.fetch(
                """
                SELECT user_id, intro_name 
                FROM users 
                WHERE finishedonboarding = true 
                AND intro_birthday IS NOT NULL
                AND EXTRACT(MONTH FROM intro_birthday) = $1
                AND EXTRACT(DAY FROM intro_birthday) = $2
                AND last_birthday_greeting_sent IS NULL
                """,
                today.month,
                today.day
            )
            
            if recently_updated_birthdays:
                logger.info(f"Found {len(recently_updated_birthdays)} users with recently updated birthdays")
                # Send greetings to users whose birthday was recently updated
                for row in recently_updated_birthdays:
                    user_id = row['user_id']
                    user_name = row['intro_name'] or "there"
                    logger.info(f"Sending birthday greeting for recently updated birthday (user {user_id})")
                    await send_birthday_greeting(bot, user_id, user_name, pool, force_send=False)
                    await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in check_recently_updated_birthday_greetings: {e}")


async def check_and_send_birthday_greetings(bot: Bot, pool: asyncpg.pool.Pool) -> None:
    """Check for birthdays today and send greetings (daily check)"""
    # Check if birthday functionality is enabled
    if not is_birthday_functionality_enabled():
        logger.info("Birthday functionality is disabled (BIRTHDAYS=No), but continuing for testing...")
        # Don't return, continue for testing purposes
    
    try:
        birthday_users = await get_birthday_users(pool)
        
        if not birthday_users:
            logger.info("No birthday users found today")
            return
        
        logger.info(f"Found {len(birthday_users)} users with birthdays today")
        
        # Send birthday greetings to all users
        # This will skip users who already received greeting today (last_birthday_greeting_sent = today)
        successful_sends = 0
        for user in birthday_users:
            user_id = user['user_id']
            user_name = user['intro_name'] or "there"
            
            success = await send_birthday_greeting(bot, user_id, user_name, pool, force_send=False)
            if success:
                successful_sends += 1
            
            # Small delay between messages to avoid rate limiting
            await asyncio.sleep(0.5)
        
        logger.info(f"Birthday greetings: {successful_sends}/{len(birthday_users)} sent successfully")
        
    except Exception as e:
        logger.error(f"Error in check_and_send_birthday_greetings: {e}")


async def get_birthday_users(pool: asyncpg.pool.Pool) -> List[Dict[str, Any]]:
    """Get users who have birthday today"""
    try:
        today = date.today()
        async with pool.acquire() as conn:
            # Get users whose birthday is today (month and day match)
            rows = await conn.fetch(
                """
                SELECT user_id, intro_name, intro_birthday 
                FROM users 
                WHERE finishedonboarding = true 
                AND intro_birthday IS NOT NULL
                AND EXTRACT(MONTH FROM intro_birthday) = $1
                AND EXTRACT(DAY FROM intro_birthday) = $2
                """,
                today.month,
                today.day
            )
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting birthday users: {e}")
        return []


async def get_upcoming_birthdays(pool: asyncpg.pool.Pool, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Get users who have birthdays in the next N days (for future features)"""
    try:
        async with pool.acquire() as conn:
            # This is a more complex query to handle year boundaries
            rows = await conn.fetch(
                """
                SELECT user_id, intro_name, intro_birthday 
                FROM users 
                WHERE finishedonboarding = true 
                AND intro_birthday IS NOT NULL
                AND (
                    (EXTRACT(MONTH FROM intro_birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
                     AND EXTRACT(DAY FROM intro_birthday) BETWEEN EXTRACT(DAY FROM CURRENT_DATE) 
                     AND EXTRACT(DAY FROM CURRENT_DATE + INTERVAL '%s days'))
                    OR
                    (EXTRACT(MONTH FROM intro_birthday) = EXTRACT(MONTH FROM CURRENT_DATE + INTERVAL '%s days')
                     AND EXTRACT(DAY FROM intro_birthday) <= EXTRACT(DAY FROM CURRENT_DATE + INTERVAL '%s days'))
                )
                ORDER BY 
                    EXTRACT(MONTH FROM intro_birthday),
                    EXTRACT(DAY FROM intro_birthday)
                """ % (days_ahead, days_ahead, days_ahead)
            )
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting upcoming birthdays: {e}")
        return []
