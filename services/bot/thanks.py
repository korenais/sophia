import re
import logging
import asyncpg
from typing import List, Dict, Tuple, Optional
from aiogram.types import Message, MessageEntity
from aiogram.fsm.context import FSMContext
from validators import UsernameValidator

logger = logging.getLogger(__name__)


def extract_text_by_utf16_offset(text: str, offset: int, length: int) -> str:
    """
    Extract text from message using UTF-16 code units offset/length.
    
    IMPORTANT: aiogram may provide offset/length in different formats depending on version.
    This function tries both UTF-16 code units and Unicode code points to ensure compatibility.
    
    Args:
        text: The message text
        offset: Offset (may be UTF-16 code units or Unicode code points)
        length: Length (may be UTF-16 code units or Unicode code points)
    
    Returns:
        Extracted text substring
    """
    # First, try direct Unicode slicing (in case aiogram already converted)
    # This is the simplest and most reliable method
    try:
        direct_result = text[offset:offset + length]
        # Validate: if result makes sense (not empty, reasonable length), use it
        if direct_result and len(direct_result.strip()) > 0:
            logger.debug(f"Using direct Unicode slicing: offset={offset}, length={length}, result='{direct_result}'")
            return direct_result.strip()
    except (IndexError, AttributeError):
        pass
    
    # If direct slicing didn't work or gave wrong result, try UTF-16 conversion
    try:
        # Convert Python string to UTF-16 bytes to count code units
        utf16_bytes = text.encode('utf-16-le')
        
        # Calculate byte positions (each UTF-16 code unit is 2 bytes)
        start_byte = offset * 2
        end_byte = (offset + length) * 2
        
        # Validate byte range
        if start_byte < 0 or end_byte > len(utf16_bytes):
            logger.warning(f"UTF-16 byte range out of bounds: start={start_byte}, end={end_byte}, total={len(utf16_bytes)}")
            # Fallback to direct slicing
            return text[offset:offset + length] if offset < len(text) else ""
        
        # Extract UTF-16 bytes
        extracted_bytes = utf16_bytes[start_byte:end_byte]
        
        # Decode back to string
        extracted_text = extracted_bytes.decode('utf-16-le')
        logger.debug(f"Using UTF-16 conversion: offset={offset}, length={length}, result='{extracted_text}'")
        return extracted_text.strip()
    except (IndexError, UnicodeDecodeError, UnicodeEncodeError) as e:
        logger.warning(f"Error extracting text with UTF-16 offset: {e}, falling back to simple slicing")
        # Fallback: try simple slicing (works for most BMP characters)
        try:
            return text[offset:offset + length] if offset < len(text) else ""
        except IndexError:
            return ""

# Bot messages for thanks system
THANKS_MESSAGES = {
    "en": {
        "START": "Hello! Give thanks: /thanks @username or just 'thanks @username'\nCommands: /thanks, /stats, /top [N]",
        "NO_USERNAME": "Specify who to thank: @username",
        "SELF_THANK": "You can't thank yourself.",
        "THANKS_GIVEN": "Thanks given!",
        "NO_THANKS": "No thanks given yet.",
        "TOP_TITLE": "Top {n} most thanked users:",
        "STATS_TITLE": "Thanks statistics:"
    },
    "ru": {
        "START": "Привет! Отмечай благодарности: /thanks @username или просто 'спасибо @username'\nКоманды: /thanks, /stats, /top [N]",
        "NO_USERNAME": "Укажи, кому благодарность: @username",
        "SELF_THANK": "Ты не можешь поблагодарить сам себя.",
        "THANKS_GIVEN": "Благодарность отправлена!",
        "NO_THANKS": "Пока нет ни одной благодарности.",
        "TOP_TITLE": "Топ {n} самых благодарных пользователей:",
        "STATS_TITLE": "Статистика благодарностей:"
    }
}

def _stars(total: int) -> str:
    """Generate star emojis for visual representation (max 3 stars)"""
    return "⭐️" * min(total, 3)

async def add_thanks(pool: asyncpg.pool.Pool, sender_user_id: int, sender_username: str, receiver_username: str) -> bool:
    """Add a thanks record to the database"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO public.thanks (sender_user_id, receiver_username, sender_username)
                VALUES ($1, $2, $3)
                """,
                sender_user_id, receiver_username, sender_username
            )
        return True
    except Exception as e:
        logger.error(f"Error adding thanks: {e}")
        return False

async def get_user_display_name(pool: asyncpg.pool.Pool, identifier: str, bot=None) -> str:
    """Get user's display name (real name + username) from database and Telegram API
    identifier can be username or name
    """
    try:
        logger.debug(f"get_user_display_name called with identifier='{identifier}'")
        async with pool.acquire() as conn:
            # Try to find by username first
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, user_telegram_link
                FROM public.users
                WHERE user_telegram_link = $1 OR intro_name = $1
                """,
                identifier
            )
            
            if row:
                logger.debug(f"Found user in DB: user_id={row['user_id']}, intro_name='{row['intro_name']}', user_telegram_link='{row['user_telegram_link']}'")
                user_id = row['user_id']
                stored_name = row['intro_name']
                telegram_link = row['user_telegram_link']
                
                # Try to get real name from Telegram API if bot is available
                real_name = stored_name
                if bot and user_id:
                    try:
                        chat_member = await bot.get_chat(user_id)
                        if chat_member.first_name or chat_member.last_name:
                            telegram_name = f"{chat_member.first_name or ''} {chat_member.last_name or ''}".strip()
                            if telegram_name:
                                real_name = telegram_name
                    except Exception:
                        # Fall back to stored name
                        pass
                
                # Check if telegram_link is a real Telegram username (numeric = user_id, not username)
                # Telegram usernames: 5-32 chars, alphanumeric + underscore, cannot be all digits
                is_real_username = telegram_link and (
                    not telegram_link.isdigit() and  # Not a pure number (user_id)
                    len(telegram_link) >= 5 and  # Telegram username minimum length
                    len(telegram_link) <= 32 and  # Telegram username maximum length
                    telegram_link.replace('_', '').isalnum()  # Only alphanumeric + underscore
                )
                
                if real_name and is_real_username:
                    # Real username - show as @username with link
                    display_name = f"{real_name} (@{telegram_link})"
                    return display_name
                elif real_name and telegram_link and telegram_link.isdigit():
                    # User ID stored - use tg://user?id= format for clickable link
                    # Format: <a href="tg://user?id=123456789">User Name</a>
                    user_id = int(telegram_link)
                    display_name = f'<a href="tg://user?id={user_id}">{real_name}</a>'
                    logger.debug(f"Returning HTML link for user_id={user_id}: {display_name}")
                    return display_name
                elif real_name:
                    # No username or user_id - show name only
                    display_name = real_name
                    return display_name
                elif is_real_username:
                    display_name = f"@{telegram_link}"
                    return display_name
                elif telegram_link and telegram_link.isdigit():
                    # User ID only - try to get name from Telegram
                    user_id = int(telegram_link)
                    if bot:
                        try:
                            chat_info = await bot.get_chat(user_id)
                            if chat_info.first_name or chat_info.last_name:
                                name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".strip()
                                return f'<a href="tg://user?id={user_id}">{name}</a>'
                        except Exception:
                            pass
                    return f'<a href="tg://user?id={user_id}">User {user_id}</a>'
                else:
                    display_name = real_name or identifier
                    return display_name
            else:
                # If not found, check if identifier is a user_id (numeric string)
                logger.debug(f"User not found in DB for identifier='{identifier}', checking if it's a user_id")
                if identifier.isdigit():
                    try:
                        user_id = int(identifier)
                        logger.debug(f"Identifier is numeric user_id={user_id}, trying to get name from Telegram")
                        if bot:
                            try:
                                chat_info = await bot.get_chat(user_id)
                                if chat_info.first_name or chat_info.last_name:
                                    name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".strip()
                                    result = f'<a href="tg://user?id={user_id}">{name}</a>'
                                    logger.debug(f"Returning HTML link from Telegram API: {result}")
                                    return result
                            except Exception as e:
                                logger.debug(f"Could not get chat info for user_id={user_id}: {e}")
                        result = f'<a href="tg://user?id={user_id}">User {user_id}</a>'
                        logger.debug(f"Returning HTML link (fallback): {result}")
                        return result
                    except ValueError:
                        pass
                # For username identifiers, add @
                if identifier.startswith('@'):
                    return identifier
                # Check if it looks like a username (not all digits, 5-32 chars)
                if not identifier.isdigit() and 5 <= len(identifier) <= 32:
                    return f"@{identifier}" if not identifier.startswith('@') else identifier
                # If identifier is numeric (user_id), create tg:// link even if not found in DB
                if identifier.isdigit():
                    try:
                        user_id = int(identifier)
                        if bot:
                            try:
                                chat_info = await bot.get_chat(user_id)
                                if chat_info.first_name or chat_info.last_name:
                                    name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".strip()
                                    return f'<a href="tg://user?id={user_id}">{name}</a>'
                            except Exception:
                                pass
                        return f'<a href="tg://user?id={user_id}">User {user_id}</a>'
                    except ValueError:
                        pass
                return identifier
    except Exception as e:
        logger.error(f"Error getting user display name: {e}")
        # If identifier is numeric (user_id), create tg:// link
        if identifier.isdigit():
            try:
                user_id = int(identifier)
                if bot:
                    try:
                        chat_info = await bot.get_chat(user_id)
                        if chat_info.first_name or chat_info.last_name:
                            name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".strip()
                            return f'<a href="tg://user?id={user_id}">{name}</a>'
                    except Exception:
                        pass
                return f'<a href="tg://user?id={user_id}">User {user_id}</a>'
            except ValueError:
                pass
        return f"@{identifier}" if not identifier.startswith('@') and not identifier.isdigit() else identifier

async def get_thanks_stats(pool: asyncpg.pool.Pool) -> List[Tuple[str, int]]:
    """Get thanks statistics ordered by total count"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT receiver_username, COUNT(*) as total
            FROM public.thanks
            GROUP BY receiver_username
            ORDER BY total DESC, receiver_username ASC
            """
        )
        return [(row['receiver_username'], row['total']) for row in rows]

async def get_top_thanks(pool: asyncpg.pool.Pool, limit: int = 5) -> List[Tuple[str, int]]:
    """Get top N users by thanks count"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT receiver_username, COUNT(*) as total
            FROM public.thanks
            GROUP BY receiver_username
            ORDER BY total DESC, receiver_username ASC
            LIMIT $1
            """,
            limit
        )
        return [(row['receiver_username'], row['total']) for row in rows]

async def find_user_by_mention(db_pool: asyncpg.pool.Pool, mention: str) -> Optional[Dict]:
    """Find user by username or name. Returns user info dict or None.
    
    Supports formats:
    - @username
    - username
    - t.me/username
    - https://t.me/username
    """
    mention = mention.strip()
    if not mention:
        return None
    
    # Normalize mention: remove @, extract from t.me/username if present
    normalized_mention = mention
    if normalized_mention.startswith('@'):
        normalized_mention = normalized_mention[1:]
    if 't.me/' in normalized_mention:
        # Extract username from t.me/username or https://t.me/username
        parts = normalized_mention.split('t.me/')
        if len(parts) > 1:
            normalized_mention = parts[-1].split('?')[0].split('#')[0].strip()
    
    async with db_pool.acquire() as conn:
        # First try to find by username (if it's a valid Telegram username)
        if UsernameValidator.is_valid_telegram_username(normalized_mention):
            # Try exact match
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, user_telegram_link
                FROM public.users
                WHERE user_telegram_link = $1
                """,
                normalized_mention
            )
            if row:
                return dict(row)
            # Try case-insensitive match
            row = await conn.fetchrow(
                """
                SELECT user_id, intro_name, user_telegram_link
                FROM public.users
                WHERE LOWER(user_telegram_link) = LOWER($1)
                """,
                normalized_mention
            )
            if row:
                return dict(row)
        
        # If not found by username, try to find by name (case-insensitive, partial match)
        # Match if mention is contained in intro_name or vice versa
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, user_telegram_link
            FROM public.users
            WHERE LOWER(intro_name) LIKE LOWER($1) OR LOWER($1) LIKE LOWER('%' || intro_name || '%')
            ORDER BY 
                CASE 
                    WHEN LOWER(intro_name) = LOWER($1) THEN 1  -- Exact match first
                    WHEN LOWER(intro_name) LIKE LOWER($1 || '%') THEN 2  -- Starts with
                    WHEN LOWER(intro_name) LIKE LOWER('%' || $1 || '%') THEN 3  -- Contains
                    ELSE 4
                END,
                intro_name
            LIMIT 1
            """,
            f"%{mention}%"
        )
        if row:
            return dict(row)
    
    return None


async def handle_thanks_command(message: Message, db_pool: asyncpg.pool.Pool, language: str = "en", bot=None):
    """Handle /thanks command
    
    Supports multiple ways to mention users:
    1. By username: @username (via message.entities with type='mention')
    2. By name: @Имя (via message.entities with type='text_mention' - contains user_id)
    3. By text extraction: fallback to finding by username/name in database
    """
    from scenes import get_messages_dynamic
    messages = get_messages_dynamic()
    
    sender_user_id = message.from_user.id
    sender_username = message.from_user.username or message.from_user.first_name or "Unknown"
    text = message.text or ""
    original_text = (message.text or "").strip()  # Preserve original text for t.me/ mentions
    
    found_users = []
    
    # First, try to extract users from message entities (most reliable method)
    if message.entities:
        logger.info(f"Processing message entities: {[e.type for e in message.entities]}")
        for entity in message.entities:
            if entity.type == 'text_mention' and entity.user:
                # User mentioned by name (Telegram provides user_id directly)
                user_id = entity.user.id
                entity_user = entity.user
                
                # Get user name from entity.user (most reliable - directly from Telegram API)
                # Telegram Bot API provides user.first_name and user.last_name from user's profile
                # Note: This may be in a different language than what user sees in @ mention list,
                # but it's the most reliable source without parsing text
                entity_first_name = entity_user.first_name or ""
                entity_last_name = entity_user.last_name or ""
                profile_name = f"{entity_first_name} {entity_last_name}".strip()
                
                # Try to extract the actual text that was mentioned from the message
                # This is how the user was mentioned in the message (e.g., "Лена Мандыч" not "Jelena Man")
                # This is useful for displaying the exact name user typed/selected, but parsing can be unreliable
                # due to UTF-16/Unicode conversion issues with emojis
                mentioned_text = ""
                if hasattr(entity, 'offset') and hasattr(entity, 'length') and message.text:
                    try:
                        # Try to extract using offset/length
                        # Note: aiogram may provide offset in Unicode code points or UTF-16 code units
                        raw_extracted = extract_text_by_utf16_offset(
                            message.text, 
                            entity.offset, 
                            entity.length
                        )
                        mentioned_text = raw_extracted.strip() if raw_extracted else ""
                        
                        logger.info(f"Extracted mentioned text from message: '{mentioned_text}' (offset={entity.offset}, length={entity.length}, message_length={len(message.text)}, profile_name='{profile_name}')")
                        
                        # Validate extraction - if result seems wrong (too short), use profile name as fallback
                        if not mentioned_text or len(mentioned_text) < 2:
                            logger.debug(f"Extracted text too short or empty, using profile name as fallback: '{profile_name}'")
                            mentioned_text = None  # Mark as invalid, will use profile_name
                        # If extracted text is very short compared to profile name, prefer profile name (more reliable)
                        elif len(mentioned_text) < len(profile_name) * 0.3:
                            logger.debug(f"Extracted text '{mentioned_text}' seems too short compared to profile name '{profile_name}', using profile name as fallback")
                            mentioned_text = None  # Mark as invalid, will use profile_name
                    except (IndexError, AttributeError) as e:
                        logger.warning(f"Could not extract mentioned text using offset/length: {e}, using profile name as fallback")
                        mentioned_text = None
                    except Exception as e:
                        logger.error(f"Unexpected error extracting mentioned text: {e}, using profile name as fallback")
                        mentioned_text = None
                else:
                    # No offset/length available, use profile name
                    mentioned_text = None
                    logger.debug(f"No offset/length in entity, using profile name: '{profile_name}'")
                
                # PRIORITY: Use extracted mentioned_text if valid (this is what user sees in @ mention list)
                # FALLBACK: Use profile_name (from Telegram API) if extraction failed or was invalid
                # This ensures we show the name user typed/selected when possible, but fallback to reliable API data
                if mentioned_text:
                    display_name = mentioned_text
                    logger.debug(f"Using extracted mentioned text as display_name: '{display_name}'")
                else:
                    display_name = profile_name
                    logger.debug(f"Using profile name as display_name: '{display_name}' (extracted text was invalid or unavailable)")
                
                logger.info(f"Found text_mention entity: user_id={user_id}, mentioned_text='{mentioned_text}', first_name='{entity_user.first_name}', last_name='{entity_user.last_name}', username='{entity_user.username}'")
                
                if user_id == sender_user_id:
                    logger.info(f"Self-thanks detected (text_mention): user_id={user_id}")
                    from scenes import get_messages_dynamic
                    messages = get_messages_dynamic()
                    await message.answer(messages["COMMANDS"]["THANKS_SELF_THANK"])
                    return  # Exit early - don't process further
                
                # Get user info from database, or create minimal record if not exists
                async with db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT user_id, intro_name, user_telegram_link
                        FROM public.users
                        WHERE user_id = $1
                        """,
                        user_id
                    )
                    
                    if row:
                        # User exists in database
                        user_info = dict(row)
                        receiver_identifier = user_info.get('user_telegram_link') or user_info.get('intro_name') or str(user_id)
                        # Use display_name (from profile_name with fallback to mentioned_text) for response
                        # This ensures we show a reliable name (from Telegram API) or fallback to extracted text
                        response_display_name = display_name or user_info.get('intro_name') or str(user_id)
                        logger.debug(f"Found existing user {user_id}: display_name='{display_name}', stored_name='{user_info.get('intro_name')}', using response_display_name='{response_display_name}'")
                        
                        # Store display_name in found_users for later use in response
                        found_users.append({
                            'user_id': user_id,
                            'identifier': receiver_identifier,
                            'display_name': display_name,  # Use display_name (from profile_name or mentioned_text)
                            'entity_name': mentioned_text  # Store mentioned text separately (for reference)
                        })
                        logger.info(f"Added existing user to found_users: user_id={user_id}, identifier='{receiver_identifier}', display_name='{display_name}', entity_name='{mentioned_text}'")
                        continue  # Skip to next entity
                    else:
                        # User not in database - create record with maximum available data from Telegram
                        # Extract all available data from entity.user (this contains name from Telegram mention)
                        entity_user = entity.user
                        first_name = entity_user.first_name or ""
                        last_name = entity_user.last_name or ""
                        full_name = f"{first_name} {last_name}".strip() or "User"
                        username = entity_user.username  # Raw username from Telegram (may be None)
                        language_code = getattr(entity_user, 'language_code', None)
                        
                        # Normalize username for user_telegram_link (required field)
                        # user_telegram_link should be in format: username (without @, t.me/, etc.)
                        # This is what we can get from Telegram: @username, username, or t.me/username
                        user_telegram_link = None
                        if username:
                            # Normalize: remove @ if present, extract from t.me/username if present
                            normalized_username = username.strip()
                            if normalized_username.startswith('@'):
                                normalized_username = normalized_username[1:]
                            if 't.me/' in normalized_username:
                                # Extract username from t.me/username
                                parts = normalized_username.split('t.me/')
                                if len(parts) > 1:
                                    normalized_username = parts[-1].split('?')[0].split('#')[0]
                            user_telegram_link = normalized_username if normalized_username else None
                        
                        logger.info(f"Creating new user from mention: user_id={user_id}, name='{full_name}', username={username}, user_telegram_link={user_telegram_link}, language={language_code}")
                        
                        # Try to get additional data from Telegram API if bot is available
                        # This can provide more complete user profile information
                        bio = None
                        if bot:
                            try:
                                # Try to get chat info (works in private chats and may provide bio)
                                chat_info = await bot.get_chat(user_id)
                                # chat_info might have more fields than entity.user
                                if hasattr(chat_info, 'first_name') and chat_info.first_name:
                                    first_name = chat_info.first_name
                                if hasattr(chat_info, 'last_name') and chat_info.last_name:
                                    last_name = chat_info.last_name
                                if hasattr(chat_info, 'username') and chat_info.username:
                                    username = chat_info.username
                                    # Update user_telegram_link with normalized username from API
                                    normalized_username = username.strip()
                                    if normalized_username.startswith('@'):
                                        normalized_username = normalized_username[1:]
                                    if 't.me/' in normalized_username:
                                        parts = normalized_username.split('t.me/')
                                        if len(parts) > 1:
                                            normalized_username = parts[-1].split('?')[0].split('#')[0]
                                    user_telegram_link = normalized_username if normalized_username else user_telegram_link
                                # Bio is available in private chats via getChat
                                if hasattr(chat_info, 'bio') and chat_info.bio:
                                    bio = chat_info.bio
                                full_name = f"{first_name} {last_name}".strip() or "User"
                            except Exception as e:
                                logger.debug(f"Could not get additional user data from Telegram API for {user_id}: {e}")
                        
                        # user_telegram_link is required - if still None, use user_id directly
                        # According to Telegram Bot API best practices: use user_id as primary identifier
                        # For users without username, we store user_id as string in user_telegram_link
                        # This allows us to reference the user by ID, not by non-existent username
                        if not user_telegram_link:
                            # Store user_id directly as string - this is the reliable identifier
                            # Format: just the user_id as string (e.g., "1735364345")
                            # We'll use tg://user?id=<user_id> for links in display
                            user_telegram_link = str(user_id)
                            logger.info(f"User {user_id} ({full_name}) has no Telegram username - storing user_id as identifier: {user_telegram_link}")
                        
                        # Create user record with maximum available data
                        # Note: Birthday is NOT available via Telegram Bot API (privacy restriction)
                        # Bio is only available in private chats via getChat, may be None in groups
                        # user_telegram_link is required field - contains normalized username from Telegram
                        
                        # Create vector_description - use bio if available, otherwise create default vector
                        # This ensures users can use /my_matches even if they don't have a description yet
                        vector_description = None
                        if bio and len(bio.strip()) >= 10:
                            try:
                                from services.bot.vectorization import vectorize_description
                                vector_description = await vectorize_description(bio)
                            except Exception as e:
                                logger.warning(f"Failed to vectorize bio for user {user_id}: {e}")
                        
                        # If no vector was created (no bio or vectorization failed), create default vector
                        if vector_description is None:
                            try:
                                from services.bot.vectorization import create_default_vector
                                vector_description = await create_default_vector()
                                logger.info(f"Created default vector for user {user_id} from thanks command")
                            except Exception as e:
                                logger.warning(f"Failed to create default vector for user {user_id}: {e}")
                                # Fallback: use zero vector (3072 dimensions for text-embedding-3-large)
                                vector_description = [0.0] * 3072
                        
                        try:
                            await conn.execute(
                                """
                                INSERT INTO public.users (
                                    user_id, intro_name, user_telegram_link, language, 
                                    intro_description, state, finishedonboarding, vector_description, created_at, updated_at
                                )
                                VALUES ($1, $2, $3, $4, $5, 'ACTIVE', true, $6, now(), now())
                                ON CONFLICT (user_id) DO UPDATE SET
                                    intro_name = COALESCE(EXCLUDED.intro_name, users.intro_name),
                                    user_telegram_link = COALESCE(EXCLUDED.user_telegram_link, users.user_telegram_link),
                                    language = COALESCE(EXCLUDED.language, users.language),
                                    intro_description = COALESCE(EXCLUDED.intro_description, users.intro_description),
                                    finishedonboarding = COALESCE(users.finishedonboarding, EXCLUDED.finishedonboarding),
                                    vector_description = COALESCE(users.vector_description, EXCLUDED.vector_description),
                                    updated_at = now()
                                """,
                                user_id,
                                full_name,
                                user_telegram_link,  # Required field: normalized Telegram username or user_id
                                language_code or "en",
                                bio,  # Bio from Telegram (if available in private chat)
                                vector_description  # Vector for matching
                            )
                            logger.info(f"Created/updated user record for {user_id} ({full_name}) from thanks mention" + 
                                       (f" with user_telegram_link={user_telegram_link}" if user_telegram_link else " (no username)") +
                                       (f" with bio" if bio else ""))
                        except Exception as e:
                            logger.warning(f"Could not create user record for {user_id}: {e}")
                        
                        # Use entity data for identifier and display
                        # For users without username, use user_id directly as identifier (best practice)
                        # This ensures we can always reference the user correctly
                        if user_telegram_link and not user_telegram_link.isdigit():
                            # Real username available - use it
                            receiver_identifier = user_telegram_link
                        else:
                            # No username - use user_id as identifier (stored as string)
                            receiver_identifier = str(user_id)
                        # Use display_name (from profile_name with fallback to mentioned_text) for display
                        # This ensures we show a reliable name from Telegram API
                        user_display_name = display_name or full_name
                        logger.info(f"Created user record: user_id={user_id}, mentioned_text='{mentioned_text}', display_name='{display_name}', profile_name='{profile_name}', user_telegram_link='{user_telegram_link}', receiver_identifier='{receiver_identifier}'")
                    
                    found_users.append({
                        'user_id': user_id,
                        'identifier': receiver_identifier,
                        'display_name': display_name,  # Use display_name (from profile_name or mentioned_text)
                        'entity_name': mentioned_text  # Store mentioned text separately (for reference)
                    })
                    logger.info(f"Added user to found_users: user_id={user_id}, identifier='{receiver_identifier}', display_name='{display_name}', entity_name='{mentioned_text}'")
            
            elif entity.type == 'mention':
                # User mentioned by username (@username)
                # Extract username from entity - use original text, not lowercased
                original_text = message.text or ""
                mention_text = original_text[entity.offset:entity.offset + entity.length]
                username = mention_text[1:] if mention_text.startswith('@') else mention_text  # Remove @
                
                logger.info(f"Found mention entity: username='{username}', mention_text='{mention_text}', offset={entity.offset}, length={entity.length}, original_text='{original_text}'")
                
                if not username:
                    logger.warning(f"Empty username extracted from mention entity")
                    continue
                
                logger.info(f"Searching for user in database: username='{username}', sender_user_id={sender_user_id}, sender_username='{sender_username}'")
                
                # Find user by username in database
                # Try exact match first, then case-insensitive match
                async with db_pool.acquire() as conn:
                    # First try exact match
                    logger.debug(f"Trying exact match for username '{username}'")
                    row = await conn.fetchrow(
                        """
                        SELECT user_id, intro_name, user_telegram_link
                        FROM public.users
                        WHERE user_telegram_link = $1
                        """,
                        username
                    )
                    if row:
                        logger.info(f"Found user with exact match: user_id={row['user_id']}, user_telegram_link='{row['user_telegram_link']}', intro_name='{row['intro_name']}'")
                    else:
                        # Try case-insensitive match
                        logger.debug(f"Exact match failed for username '{username}', trying case-insensitive match")
                        row = await conn.fetchrow(
                            """
                            SELECT user_id, intro_name, user_telegram_link
                            FROM public.users
                            WHERE LOWER(user_telegram_link) = LOWER($1)
                            """,
                            username
                        )
                        if row:
                            logger.info(f"Found user with case-insensitive match: user_id={row['user_id']}, stored='{row['user_telegram_link']}', searched='{username}'")
                        else:
                            logger.warning(f"User not found in database: username='{username}'")
                    
                    if row:
                        user_info = dict(row)
                        if user_info['user_id'] == sender_user_id:
                            logger.info(f"Self-thanks detected: user_id={user_info['user_id']}, username='{username}'")
                            from scenes import get_messages_dynamic
                            messages = get_messages_dynamic()
                            await message.answer(messages["COMMANDS"]["THANKS_SELF_THANK"])
                            return  # Exit early - don't process further
                        receiver_identifier = user_info.get('user_telegram_link') or user_info.get('intro_name') or username
                        found_users.append({
                            'user_id': user_info['user_id'],
                            'identifier': receiver_identifier,
                            'display_name': user_info.get('intro_name') or receiver_identifier
                        })
                        logger.info(f"Added user to found_users: user_id={user_info['user_id']}, username='{username}', display_name='{user_info.get('intro_name') or receiver_identifier}'")
                    else:
                        # User not found in database - try to get user info from Telegram API
                        logger.info(f"User with username '{username}' not found in database, trying to get from Telegram API")
                        if bot:
                            try:
                                # Try to get user by username from Telegram
                                # Note: get_chat works with usernames (without @)
                                chat_info = await bot.get_chat(f"@{username}")
                                user_id = chat_info.id
                                first_name = getattr(chat_info, 'first_name', None) or ""
                                last_name = getattr(chat_info, 'last_name', None) or ""
                                full_name = f"{first_name} {last_name}".strip() or "User"
                                language_code = getattr(chat_info, 'language_code', None)
                                bio = getattr(chat_info, 'bio', None)
                                
                                logger.info(f"Got user info from Telegram API: user_id={user_id}, name='{full_name}', username='{username}'")
                                
                                # Create vector_description for new user
                                vector_description = None
                                if bio and len(bio.strip()) >= 10:
                                    try:
                                        from services.bot.vectorization import vectorize_description
                                        vector_description = await vectorize_description(bio)
                                    except Exception as e:
                                        logger.warning(f"Failed to vectorize bio for user {user_id}: {e}")
                                
                                if vector_description is None:
                                    try:
                                        from services.bot.vectorization import create_default_vector
                                        vector_description = await create_default_vector()
                                    except Exception as e:
                                        logger.warning(f"Failed to create default vector for user {user_id}: {e}")
                                        vector_description = [0.0] * 3072
                                
                                # Create user record
                                await conn.execute(
                                    """
                                    INSERT INTO public.users (
                                        user_id, intro_name, user_telegram_link, language, 
                                        intro_description, state, finishedonboarding, vector_description, created_at, updated_at
                                    )
                                    VALUES ($1, $2, $3, $4, $5, 'ACTIVE', true, $6, now(), now())
                                    ON CONFLICT (user_id) DO UPDATE SET
                                        intro_name = COALESCE(EXCLUDED.intro_name, users.intro_name),
                                        user_telegram_link = COALESCE(EXCLUDED.user_telegram_link, users.user_telegram_link),
                                        language = COALESCE(EXCLUDED.language, users.language),
                                        intro_description = COALESCE(EXCLUDED.intro_description, users.intro_description),
                                        finishedonboarding = COALESCE(EXCLUDED.finishedonboarding, users.finishedonboarding),
                                        vector_description = COALESCE(users.vector_description, EXCLUDED.vector_description),
                                        updated_at = now()
                                    """,
                                    user_id,
                                    full_name,
                                    username,  # user_telegram_link
                                    language_code or "en",
                                    bio,
                                    vector_description
                                )
                                
                                if user_id == sender_user_id:
                                    logger.debug(f"Skipping self-thanks for user_id={user_id}")
                                    continue
                                
                                found_users.append({
                                    'user_id': user_id,
                                    'identifier': username,
                                    'display_name': full_name
                                })
                                logger.info(f"Created user from mention entity: user_id={user_id}, username='{username}', display_name='{full_name}'")
                            except Exception as e:
                                logger.warning(f"Could not get user info from Telegram API for username '{username}': {e}")
                                # Fallback: will try text extraction later
                        else:
                            logger.warning(f"Bot not available, cannot get user info from Telegram API for username '{username}'")
    
    # Fallback: if no entities found, try text extraction (for backward compatibility)
    # Also handle URL entities that contain t.me/username
    if not found_users:
        # First, check if there are URL entities that contain t.me/
        if message.entities:
            for entity in message.entities:
                if entity.type == 'url' and message.text:
                    # Extract URL from message
                    url_text = original_text[entity.offset:entity.offset + entity.length]
                    if 't.me/' in url_text.lower():
                        # Extract username from t.me/username
                        parts = url_text.lower().split('t.me/')
                        if len(parts) > 1:
                            username = parts[-1].split('?')[0].split('#')[0].strip()
                            logger.info(f"Found t.me/ username in URL entity: '{username}' from URL '{url_text}'")
                            
                            # Try to find user in database
                            user_info = await find_user_by_mention(db_pool, username)
                            if user_info and user_info['user_id'] != sender_user_id:
                                # Check if user_id is positive (real user, not group/channel)
                                if user_info['user_id'] > 0:
                                    receiver_identifier = user_info.get('user_telegram_link') or user_info.get('intro_name') or username
                                    display_name = user_info.get('intro_name') or receiver_identifier
                                    
                                    # If display_name is "User" (fallback), try to update from Telegram API
                                    if display_name == "User" and bot:
                                        try:
                                            chat_info = await bot.get_chat(f"@{username}")
                                            if getattr(chat_info, 'type', None) == 'private':
                                                first_name = getattr(chat_info, 'first_name', None) or ""
                                                last_name = getattr(chat_info, 'last_name', None) or ""
                                                full_name = f"{first_name} {last_name}".strip() or username
                                                
                                                # Update user record with correct name
                                                async with db_pool.acquire() as conn:
                                                    await conn.execute(
                                                        """
                                                        UPDATE public.users
                                                        SET intro_name = $1, updated_at = now()
                                                        WHERE user_id = $2
                                                        """,
                                                        full_name,
                                                        user_info['user_id']
                                                    )
                                                display_name = full_name
                                                logger.info(f"Updated user name from Telegram API: user_id={user_info['user_id']}, name='{full_name}'")
                                        except Exception as e:
                                            logger.debug(f"Could not update user name from Telegram API: {e}")
                                    
                                    found_users.append({
                                        'user_id': user_info['user_id'],
                                        'identifier': receiver_identifier,
                                        'display_name': display_name
                                    })
                                    logger.info(f"Found user from URL entity: user_id={user_info['user_id']}, username='{username}', display_name='{display_name}'")
                                    continue  # Found user, skip to next entity
                                else:
                                    logger.warning(f"Found user_id={user_info['user_id']} for username '{username}', but it's a group/channel (negative ID). Will try Telegram API to find real user.")
                                    user_info = None  # Reset to try Telegram API
                            
                            # If not found in database, try to get from Telegram API
                            if bot and not user_info:
                                try:
                                    chat_info = await bot.get_chat(f"@{username}")
                                    chat_type = getattr(chat_info, 'type', None)
                                    user_id = chat_info.id
                                    
                                    # Only process private chats (users), skip groups/channels
                                    if chat_type != 'private':
                                        logger.warning(f"Username '{username}' is a {chat_type}, not a user. Cannot thank a {chat_type}.")
                                        # Try to find user by name in database as fallback
                                        name_match = await find_user_by_mention(db_pool, username)
                                        if name_match and name_match['user_id'] > 0 and name_match['user_id'] != sender_user_id:
                                            logger.info(f"Found user by name match: user_id={name_match['user_id']}, name='{name_match.get('intro_name')}'")
                                            found_users.append({
                                                'user_id': name_match['user_id'],
                                                'identifier': name_match.get('user_telegram_link') or name_match.get('intro_name') or username,
                                                'display_name': name_match.get('intro_name') or username
                                            })
                                        else:
                                            # Send error message explaining that username points to channel/group
                                            from scenes import get_messages_dynamic
                                            messages = get_messages_dynamic()
                                            # Translate chat_type to Russian (since bot language is Russian)
                                            # Nominative case (именительный падеж): канал, группа, супергруппа
                                            chat_type_nominative = "канал" if chat_type == "channel" else "группа" if chat_type == "group" else "супергруппа" if chat_type == "supergroup" else chat_type
                                            # Dative case (дательный падеж): каналу, группе, супергруппе
                                            chat_type_dative = "каналу" if chat_type == "channel" else "группе" if chat_type == "group" else "супергруппе" if chat_type == "supergroup" else chat_type
                                            error_msg = messages.get("COMMANDS", {}).get("THANKS_NOT_A_USER", 
                                                f"❌ @{username} — это {chat_type_nominative}, а не пользователь. Невозможно отправить благодарность {chat_type_dative}. Используйте @username реального пользователя или выберите пользователя из меню упоминаний Telegram (кнопка @).")
                                            error_msg = error_msg.format(username=username, chat_type=chat_type_nominative, chat_type_dative=chat_type_dative)
                                            await message.answer(error_msg)
                                            return  # Exit early - don't process further
                                        continue
                                    
                                    first_name = getattr(chat_info, 'first_name', None) or ""
                                    last_name = getattr(chat_info, 'last_name', None) or ""
                                    full_name = f"{first_name} {last_name}".strip()
                                    
                                    # If no name available, use username as fallback
                                    if not full_name:
                                        full_name = username
                                    
                                    language_code = getattr(chat_info, 'language_code', None)
                                    bio = getattr(chat_info, 'bio', None)
                                    
                                    logger.info(f"Got user info from Telegram API (URL entity): user_id={user_id}, name='{full_name}', username='{username}', chat_type='{chat_type}'")
                                    
                                    # Create vector_description for new user
                                    vector_description = None
                                    if bio and len(bio.strip()) >= 10:
                                        try:
                                            from services.bot.vectorization import vectorize_description
                                            vector_description = await vectorize_description(bio)
                                        except Exception as e:
                                            logger.warning(f"Failed to vectorize bio for user {user_id}: {e}")
                                    
                                    if vector_description is None:
                                        try:
                                            from services.bot.vectorization import create_default_vector
                                            vector_description = await create_default_vector()
                                        except Exception as e:
                                            logger.warning(f"Failed to create default vector for user {user_id}: {e}")
                                            vector_description = [0.0] * 3072
                                    
                                    # Create user record
                                    async with db_pool.acquire() as conn:
                                        await conn.execute(
                                            """
                                            INSERT INTO public.users (
                                                user_id, intro_name, user_telegram_link, language, 
                                                intro_description, state, finishedonboarding, vector_description, created_at, updated_at
                                            )
                                            VALUES ($1, $2, $3, $4, $5, 'ACTIVE', true, $6, now(), now())
                                            ON CONFLICT (user_id) DO UPDATE SET
                                                intro_name = COALESCE(EXCLUDED.intro_name, users.intro_name),
                                                user_telegram_link = COALESCE(EXCLUDED.user_telegram_link, users.user_telegram_link),
                                                language = COALESCE(EXCLUDED.language, users.language),
                                                intro_description = COALESCE(EXCLUDED.intro_description, users.intro_description),
                                                finishedonboarding = COALESCE(EXCLUDED.finishedonboarding, users.finishedonboarding),
                                                vector_description = COALESCE(users.vector_description, EXCLUDED.vector_description),
                                                updated_at = now()
                                            """,
                                            user_id,
                                            full_name,
                                            username,
                                            language_code or "en",
                                            bio,
                                            vector_description
                                        )
                                    
                                    if user_id != sender_user_id:
                                        found_users.append({
                                            'user_id': user_id,
                                            'identifier': username,
                                            'display_name': full_name
                                        })
                                        logger.info(f"Created user from URL entity: user_id={user_id}, username='{username}', display_name='{full_name}'")
                                except Exception as e:
                                    logger.warning(f"Could not get user info from Telegram API for username '{username}' (from URL entity): {e}")
        
        # Also try regex extraction as fallback
        if not found_users:
            # Match @username, t.me/username, or https://t.me/username
            # Pattern: @username or t.me/username (with optional https://)
            # Use original text (not lowercased) to preserve case
            raw_mentions = re.findall(r'(?:@|(?:https?://)?t\.me/)[\w\d_А-Яа-яЁё\s]+', original_text, re.IGNORECASE)
            for raw_mention in raw_mentions:
                mention = raw_mention.strip()
                if not mention:
                    continue
                
                # Normalize: remove @ or t.me/ prefix
                if mention.lower().startswith('@'):
                    mention = mention[1:].strip()
                elif 't.me/' in mention.lower():
                    # Extract username from t.me/username
                    parts = mention.lower().split('t.me/')
                    if len(parts) > 1:
                        mention = parts[-1].split('?')[0].split('#')[0].strip()
                    else:
                        continue
                else:
                    continue
                
                # Find user by mention (username or name)
                user_info = await find_user_by_mention(db_pool, mention)
                if not user_info or user_info['user_id'] == sender_user_id:
                    continue
                
                # Use username if available, otherwise use name for storage
                receiver_identifier = user_info.get('user_telegram_link') or user_info.get('intro_name') or mention
                found_users.append({
                    'user_id': user_info['user_id'],
                    'identifier': receiver_identifier,
                    'display_name': user_info.get('intro_name') or receiver_identifier
                })
    
    if not found_users:
        await message.answer(messages["COMMANDS"]["THANKS_NO_USERNAME"])
        return
    
    response_messages = []
    for user_info in found_users:
        receiver_identifier = user_info['identifier']
        receiver_user_id = user_info.get('user_id')
        # Use display_name (from profile_name with fallback to mentioned_text) for response
        # This ensures we show a reliable name from Telegram API (entity.user.full_name)
        # or fallback to extracted text if available
        display_name_from_info = user_info.get('display_name')  # This is from profile_name or mentioned_text
        entity_name = user_info.get('entity_name')  # This is the mentioned_text extracted from message (for reference)
        logger.info(f"Processing thanks for: user_id={receiver_user_id}, identifier='{receiver_identifier}', display_name='{display_name_from_info}', entity_name='{entity_name}'")
        
        # Ensure sender user exists with correct user_id (handle migration if needed)
        async with db_pool.acquire() as conn:
            existing_sender = await conn.fetchrow(
                "SELECT user_id FROM users WHERE user_id = $1",
                sender_user_id
            )
            
            # If sender doesn't exist with real ID, try to migrate from temporary ID
            if not existing_sender:
                sender_username_for_migration = message.from_user.username if hasattr(message, 'from_user') else None
                sender_first_name = message.from_user.first_name if hasattr(message, 'from_user') else None
                sender_last_name = message.from_user.last_name if hasattr(message, 'from_user') else None
                
                temp_sender = None
                # Try by username first
                if sender_username_for_migration:
                    temp_sender = await conn.fetchrow(
                        "SELECT user_id, finishedonboarding, state FROM users WHERE user_id < 0 AND LOWER(user_telegram_link) = LOWER($1)",
                        sender_username_for_migration
                    )
                # Try by name if username didn't match
                if not temp_sender and sender_first_name:
                    sender_full_name = f"{sender_first_name} {sender_last_name}".strip() if sender_last_name else sender_first_name
                    temp_sender = await conn.fetchrow(
                        "SELECT user_id, finishedonboarding, state FROM users WHERE user_id < 0 AND (intro_name ILIKE $1 OR $2 ILIKE '%' || TRIM(intro_name) || '%')",
                        f"%{sender_full_name}%", sender_full_name
                    )
                
                if temp_sender:
                    logger.info(f"Migrating sender user from {temp_sender['user_id']} to {sender_user_id} before saving thanks")
                    finishedonboarding_value = temp_sender.get('finishedonboarding', True)
                    state_value = temp_sender.get('state', 'ACTIVE')
                    await conn.execute(
                        "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                        sender_user_id, temp_sender['user_id'], finishedonboarding_value, state_value
                    )
                    # Also migrate existing thanks
                    await conn.execute(
                        "UPDATE thanks SET sender_user_id = $1 WHERE sender_user_id = $2",
                        sender_user_id, temp_sender['user_id']
                    )
                    logger.info(f"✓ Migrated sender user {temp_sender['user_id']} -> {sender_user_id} before thanks save")
        
        # Add thanks to database
        success = await add_thanks(db_pool, sender_user_id, sender_username, receiver_identifier)
        if success:
            logger.info(f"Successfully added thanks: sender={sender_user_id}, receiver_identifier='{receiver_identifier}'")
            # Get current total for this user
            stats = await get_thanks_stats(db_pool)
            total = next((count for user, count in stats if user == receiver_identifier), 0)
            
            # Use display_name_from_info if available (from profile_name or mentioned_text)
            # This is the most reliable source - directly from Telegram API
            if display_name_from_info:
                # Use display_name - this is from entity.user.full_name (most reliable)
                if receiver_identifier.isdigit():
                    # User ID - use tg://user?id= format for clickable link
                    user_id = int(receiver_identifier)
                    display_name = f'<a href="tg://user?id={user_id}">{display_name_from_info}</a>'
                else:
                    # Username - use display name with @username
                    display_name = f"{display_name_from_info} (@{receiver_identifier})"
            else:
                # Fallback: get user's display name from database/API
                display_name = await get_user_display_name(db_pool, receiver_identifier, bot)
            
            response_message = f"{display_name} {messages['COMMANDS']['THANKS_NOW_HAS']} {_stars(total)} ({total}) {messages['COMMANDS']['THANKS_WORD']}"
            response_messages.append(response_message)
            logger.info(f"Thanks response: {response_message}")
        else:
            logger.error(f"Failed to add thanks for receiver_identifier='{receiver_identifier}'")
    
    if response_messages:
        # Use HTML parse mode to support tg://user?id= links
        from aiogram.enums import ParseMode
        await message.answer("\n".join(response_messages), parse_mode=ParseMode.HTML)
    else:
        await message.answer(messages["COMMANDS"]["THANKS_SELF_THANK"])

async def handle_stats_command(message: Message, db_pool: asyncpg.pool.Pool, language: str = "en", bot=None):
    """Handle /stats command"""
    from scenes import get_messages_dynamic
    messages = get_messages_dynamic()
    
    stats = await get_thanks_stats(db_pool)
    if not stats:
        await message.answer(messages["COMMANDS"]["THANKS_NO_THANKS"])
        return
    
    lines = []
    for user, total in stats:
        display_name = await get_user_display_name(db_pool, user, bot)
        lines.append(f"{display_name} — {_stars(total)} ({total}) {messages['COMMANDS']['THANKS_WORD']}")
    
    response = f"{messages['COMMANDS']['THANKS_STATS_TITLE']}\n" + "\n".join(lines)
    await message.answer(response)

async def handle_top_command(message: Message, db_pool: asyncpg.pool.Pool, language: str = "en", bot=None):
    """Handle /top [N] command"""
    # Parse number from command arguments
    try:
        args = message.text.split()[1:] if message.text else []
        n = int(args[0]) if args else 5
        n = max(1, min(n, 50))  # Limit between 1 and 50
    except (ValueError, IndexError):
        n = 5
    
    from scenes import get_messages_dynamic
    messages = get_messages_dynamic()
    
    top_users = await get_top_thanks(db_pool, n)
    if not top_users:
        await message.answer(messages["COMMANDS"]["THANKS_NO_THANKS"])
        return
    
    lines = []
    for i, (user, total) in enumerate(top_users, 1):
        display_name = await get_user_display_name(db_pool, user, bot)
        lines.append(f"{i}. {display_name} — {_stars(total)} ({total}) {messages['COMMANDS']['THANKS_WORD']}")
    
    response = f"{messages['COMMANDS']['THANKS_TOP_TITLE'].format(n=n)}\n" + "\n".join(lines)
    await message.answer(response)

async def handle_thanks_text(message: Message, db_pool: asyncpg.pool.Pool, language: str = "en", bot=None):
    """Handle text messages that contain thanks (like 'спасибо @username' or 'thanks @username')
    
    Supports:
    - Traditional mentions with @ symbol
    - text_mention entities (user selected via Telegram UI without @)
    - mention entities (username mentions)
    """
    text = (message.text or "").strip().lower()
    original_text = (message.text or "").strip()
    
    # Check if message has any mentions (via @, t.me/, or entities)
    has_mention = False
    if "@" in original_text or "t.me/" in original_text.lower():
        has_mention = True
    elif message.entities:
        for entity in message.entities:
            if entity.type in ('text_mention', 'mention'):
                has_mention = True
                break
    
    if not has_mention:
        return  # No mentions, skip processing
    
    # List of thanks words in different languages (including variations and declensions)
    thanks_words_ru = [
        r"спасиб",       # спасибо, спасиб, спасибочки (match root "спасиб" to catch all variations)
        r"благодар",     # благодарю, благодарим, благодаришь, благодарен, благодарна, благодарны, благодарность, благодарствую
        r"мерси",        # мерси
        r"пасиб",        # пасиб, пасибо
        r"сенкс",        # сенкс (thanks транслитерация)
        r"сенкью",       # сенкью (thank you транслитерация)
        r"респект",      # респект, респектую
    ]
    
    # Ukrainian thanks words
    thanks_words_uk = [
        r"дяк",          # дякую, дякують, дякуєш, дяка (match root "дяк" to catch all variations including "дяка")
        r"спасиб",       # спасибо (also used in Ukrainian)
        r"благодар",     # благодарю, благодарний, благодарна (also used in Ukrainian)
        r"мерси",        # мерси (also used in Ukrainian)
    ]
    
    thanks_words_en = [
        r"thanks?",      # thanks, thank
        r"thank\s+you",  # thank you
        r"thx",          # thx
        r"ty\b",         # ty (but not part of other words)
        r"grateful",     # grateful
        r"appreciat",    # appreciate, appreciated, appreciating (match root to catch all forms)
        r"cheers",       # cheers (in some contexts)
    ]
    
    # Build flexible patterns that match thanks words followed by @username
    # Pattern allows for optional words between thanks word and @username
    thanks_patterns = []
    
    # Russian patterns - match any thanks word, optionally followed by other words, then @username or t.me/username
    # IMPORTANT: Require at least one space or punctuation between thanks word and mention
    # This prevents matching "спасибо@user" (invalid) but allows "спасибо @user" (valid)
    for word in thanks_words_ru:
        # Match word boundary, thanks word (with possible declensions), then whitespace/punctuation, then mention
        # Pattern: thanks_word + (whitespace/punctuation, required) + (optional text, max 50 chars) + (@username or t.me/username)
        # [\s\W] requires at least one whitespace or non-word character (punctuation)
        # Allow cyrillic and spaces in mentions for names like @Антон
        # Support both @username and t.me/username formats
        pattern = rf"(?i)\b{word}[\w]*\b[\s\W]+.{{0,50}}(?:@|(?:https?://)?t\.me/)[\w\d_А-Яа-яЁё\s]+"
        thanks_patterns.append(pattern)
    
    # Ukrainian patterns - similar to Russian, but with Ukrainian-specific words
    for word in thanks_words_uk:
        # Allow cyrillic and spaces in mentions (Ukrainian uses same alphabet as Russian)
        # Support both @username and t.me/username formats
        pattern = rf"(?i)\b{word}[\w]*\b[\s\W]+.{{0,50}}(?:@|(?:https?://)?t\.me/)[\w\d_А-Яа-яЁёІіЇїЄє\s]+"
        thanks_patterns.append(pattern)
    
    # English patterns
    for word in thanks_words_en:
        # Support both @username and t.me/username formats
        pattern = rf"(?i)\b{word}[\w]*\b[\s\W]+.{{0,50}}(?:@|(?:https?://)?t\.me/)[\w\d_]+"
        thanks_patterns.append(pattern)
    
    # Check if message matches any thanks pattern OR has mention entities
    # Pattern matching for traditional @ mentions or t.me/ mentions
    matches = []
    if "@" in original_text or "t.me/" in original_text.lower():
        # Use original text (not lowercased) for pattern matching to preserve case
        for pattern in thanks_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                matches.append(match.group())
    
    # Check if message has mention entities (text_mention or mention)
    has_mention_entities = False
    mention_entity_types = []
    if message.entities:
        for e in message.entities:
            if e.type in ('text_mention', 'mention'):
                has_mention_entities = True
                mention_entity_types.append(e.type)
    
    logger.info(f"Thanks check: text='{message.text}', original_text='{original_text}', has_@={('@' in original_text)}, has_t.me={('t.me/' in original_text.lower())}, matches={len(matches)}, has_entities={has_mention_entities}, entity_types={mention_entity_types}, matched_patterns={matches}")
    
    # If pattern matched OR has mention entities, check if thanks word is present
    if matches or has_mention_entities:
        # For mention entities without @, check if any thanks word is in the text
        if has_mention_entities and not matches:
            # Check if any thanks word appears in the text (without requiring @)
            # Use original text (not lowercased) for better matching, but check case-insensitively
            # Note: original_text is already defined at the top of handle_thanks_text function
            # Build simple word list from patterns (check both original and lowercase)
            # Include variations: спасибочки contains "спасиб", благодарна contains "благодар", дякую contains "дяк"
            simple_thanks_words = [
                "спасиб", "благодар", "мерси", "пасиб", "сенкс", "сенкью", "респект",  # Russian
                "дяк",  # Ukrainian (covers дякую, дякують, дякуєш, дяка)
                "thank", "thanks", "thx", "ty", "grateful", "appreciat", "cheers"  # English
            ]
            # Check in lowercase text for case-insensitive matching
            has_thanks_word = any(word in text for word in simple_thanks_words)
            
            logger.info(f"Entity mention without @: text='{original_text}', lowercase='{text}', has_thanks_word={has_thanks_word}, entities={[e.type for e in message.entities if e.type in ('text_mention', 'mention')]}")
            
            if not has_thanks_word:
                logger.debug(f"No thanks word found in text '{original_text}' despite having mention entities")
                return  # Has mentions but no thanks word, skip
        
        try:
            await handle_thanks_command(message, db_pool, language, bot)
        except Exception as e:
            logger.error(f"Error in handle_thanks_command: {e}")
            import traceback
            traceback.print_exc()
