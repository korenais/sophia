import asyncio
import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommandScopeChat, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonCommands, ChatMemberUpdated, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, StateFilter, ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
import asyncpg
from dotenv import load_dotenv
from openai import AsyncOpenAI
from db import get_pool, insert_feedback, get_matchable_users, get_user_language, get_user_info, block_user, disable_all_matches, enable_all_matches, get_meeting_by_id, update_meeting_status
from match_generation import generate_user_pairs
from scenes import (
    OnboardingStates, ProfileStates, MyMatchesStates, BrowseStates, start_onboarding, handle_name, handle_location,
    handle_description, handle_linkedin, handle_hobbies_drivers, handle_skills, handle_field_of_activity, handle_birthday,
    handle_birthday_callback, handle_photo, handle_profile_confirmation,
    handle_view_profile, handle_edit_profile, handle_profile_view_response, handle_profile_edit_response,
    get_messages_dynamic, get_exit_keyboard, build_profile_text,
    handle_name_edit_mode, handle_location_edit_mode, handle_description_edit_mode, handle_linkedin_edit_mode,
    handle_hobbies_drivers_edit_mode, handle_skills_edit_mode, handle_field_of_activity_edit_mode, handle_photo_edit_mode
)
from throttling import init_throttling, send_message_throttled
from middleware import (
    PrivateChatOnlyMiddleware, NoBotsMiddleware, GroupMembershipMiddleware,
    UpdateUserInteractionMiddleware, BlockBotCommandsInSceneMiddleware
)
from dm_only_middleware import DMOnlyCommandsMiddleware
from match_system import init_match_system, run_automatic_matching
from meeting_followup import init_followup_system, handle_followup_response
from username_cache import init_username_cache
from scheduler import init_scheduler, start_scheduler, stop_scheduler
from feedback_notification import init_feedback_notification, notify_feedback
from bug_reporting import init_bug_reporting
from thanks import handle_thanks_command, handle_stats_command, handle_top_command, handle_thanks_text


load_dotenv()


# Support either TELEGRAM_TOKEN or TELEGRAM_API_KEY for compatibility
# Strip whitespace to prevent issues with spaces in token
_telegram_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_API_KEY") or ""
TELEGRAM_TOKEN = _telegram_token.strip() if _telegram_token else ""
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@db:5432/postgres")
_openai_key = os.getenv("OPENAI_API_KEY") or ""
OPENAI_API_KEY = _openai_key.strip() if _openai_key else ""


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_db_pool() -> asyncpg.pool.Pool:
    return await get_pool(DB_URL)


async def check_critical_configuration(db_pool: asyncpg.Pool):
    """Check critical configuration and create bug reports for missing/invalid settings"""
    try:
        from bug_reporting import report_bug
        
        issues_found = []
        
        # Check TELEGRAM_TOKEN
        if not TELEGRAM_TOKEN:
            issues_found.append({
                "type": "config",
                "message": "TELEGRAM_TOKEN is not set - bot cannot function",
                "severity": "critical",
                "config_key": "TELEGRAM_TOKEN"
            })
        
        # Check DB_URL
        db_url = os.getenv("DB_URL")
        if not db_url:
            issues_found.append({
                "type": "config",
                "message": "DB_URL is not set - using default may not work in production",
                "severity": "high",
                "config_key": "DB_URL"
            })
        
        
        # Check BIRTHDAYS configuration if enabled
        birthdays_enabled = os.getenv("BIRTHDAYS", "No").strip().lower()
        if birthdays_enabled in ("yes", "true", "1", "on", "enabled"):
            if not os.getenv("BIRTHDAY_TOPIC_ID"):
                issues_found.append({
                    "type": "config",
                    "message": "BIRTHDAYS=Yes but BIRTHDAY_TOPIC_ID is not set - birthday greetings will fail",
                    "severity": "critical",
                    "config_key": "BIRTHDAY_TOPIC_ID"
                })
            if not os.getenv("TELEGRAM_GROUP_ID"):
                issues_found.append({
                    "type": "config",
                    "message": "BIRTHDAYS=Yes but TELEGRAM_GROUP_ID is not set - birthday greetings will fail",
                    "severity": "critical",
                    "config_key": "TELEGRAM_GROUP_ID"
                })
        
        # Report all issues found
        for issue in issues_found:
            await report_bug(
                error_type=issue["type"],
                error_message=issue["message"],
                context={
                    "missing_config": issue.get("config_key"),
                    "check_time": datetime.now().isoformat()
                },
                severity=issue["severity"]
            )
            logger.warning(f"Configuration issue detected: {issue['message']}")
        
        if issues_found:
            logger.warning(f"Found {len(issues_found)} critical configuration issue(s) - bug reports created")
        else:
            logger.info("Critical configuration check passed")
            
    except Exception as e:
        logger.error(f"Error checking critical configuration: {e}")


def get_commands_for_chat_type(chat_type: str, user_language: str = "ru") -> list:
    """Get appropriate commands based on chat type and user language"""
    
    # Load DM-only commands from environment
    dm_only_commands_env = os.getenv("DM_ONLY_COMMANDS", 
        "start,edit_profile,view_profile,my_matches,browse,people,report_an_issue,suggest_a_feature,say,confirm_match")
    dm_only_commands = set(cmd.strip() for cmd in dm_only_commands_env.split(","))
    
    # Universal commands that work in all chat types
    universal_commands = [
        BotCommand(command="help", description="Помощь" if user_language == "ru" else "Help"),
    ]
    
    if chat_type == "private":
        # Private chat - show all commands including DM-only ones
        private_commands = [
            BotCommand(command="start", description="Начать регистрацию" if user_language == "ru" else "Start registration"),
            BotCommand(command="edit_profile", description="Изменить профиль" if user_language == "ru" else "Edit profile"),
            BotCommand(command="view_profile", description="Ваш профиль" if user_language == "ru" else "Your profile"),
            BotCommand(command="my_matches", description="Ваши мэтчи (random coffee)" if user_language == "ru" else "Your matches (random coffee)"),
            BotCommand(command="browse", description="Список резидентов" if user_language == "ru" else "Residents list"),
            BotCommand(command="suggest_a_feature", description="Предложи изменение" if user_language == "ru" else "Suggest change"),
        ] + universal_commands
        
        return private_commands
        
    else:
        # Group chat - show only group-appropriate commands
        group_commands = universal_commands
        
        return group_commands

async def setup_bot_commands(bot: Bot):
    """Set up bot commands menu with dynamic commands based on chat type"""
    
    try:
        # Set commands for private chats (all commands available)
        private_commands = get_commands_for_chat_type("private")
        await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        logger.info("✅ Bot commands set for all private chats")
        
        # Set commands for group chats (limited commands)
        group_commands = get_commands_for_chat_type("group")
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("✅ Bot commands set for all group chats")
        
        # Set default commands (fallback - private chat commands)
        await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
        logger.info("✅ Bot commands set for default scope")
        
        # Set menu button to show commands
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Menu button set to show commands")
        
        logger.info("🎉 Dynamic bot commands menu set up successfully")
        
    except Exception as e:
        logger.error(f"❌ Error setting bot commands: {e}")
        try:
            # Ultimate fallback - just set basic commands
            fallback_commands = [
                BotCommand(command="help", description="Помощь"),
            ]
            await bot.set_my_commands(fallback_commands, scope=BotCommandScopeDefault())
            logger.info("✅ Fallback: Basic bot commands set for default scope only")
        except Exception as e2:
            logger.error(f"❌ Critical error setting bot commands: {e2}")


async def send_welcome_message(bot: Bot, chat_id: int, user_language: str = "ru"):
    """Send welcome message when bot is added to group"""
    try:
        if user_language == "en":
            welcome_text = """🤖 <b>Hello! I'm Sophia, your chat bot!</b>

Nice to meet you! I'm here to help you connect with other people and find meaningful matches.

<b>Quick start:</b>
• Use /start to begin registration
• Use /menu to see all available options
• Use /help for assistance

I'm excited to help you make new connections! 💫"""
        else:  # Russian (default)
            welcome_text = """Привет! Я Алекса, ИИ-консьерж Baltic Business Club.

Помогаю держать Клуб в порядке и делать его живым.

- собираю базу резидентов (заполните профиль — это важно)
- подбираю ближайшие мэтчи через Random Coffee
- считаю благодарности и показываю, кто кого поддерживает

Постепенно я становлюсь Клубным консьержем - буду помнить ваш опыт, связи и интересы, чтобы помогать быстрее находить нужных людей и решения.

Напиши мне в ЛС, "/start" чтобы проверить информацию или заполнить свой профиль. 

Пишите, знакомьтесь, пользуйтесь - я здесь, чтобы Клуб работал как единая сеть.

ps. хоть ко мне подключены все последние библиотеки GPT, я использую их только для сбора информации и мэтчей вас с резидентами. На данный момент функционал активной коммуникации у меня отключен - я не смогу ответить вам на прямые сообщения."""
        
        await bot.send_message(chat_id, welcome_text)
        logger.info(f"✅ Welcome message sent to chat {chat_id} in {user_language}")
        
    except Exception as e:
        logger.error(f"❌ Error sending welcome message to chat {chat_id}: {e}")


async def on_start(message: Message):
    from scenes import get_messages_dynamic
    messages = get_messages_dynamic(message.from_user.id)
    await message.answer(messages["COMMANDS"]["BOT_UP"])


# --- Helper function to check and process thanks messages ---
async def _check_and_process_thanks(message: Message, db_pool, bot) -> bool:
    """Check if message is a thanks message and process it. Returns True if processed.
    
    Checks for:
    1. @ symbol in text (traditional mentions)
    2. text_mention entities (user selected via Telegram UI without @)
    3. mention entities (username mentions)
    """
    text = message.text or ""
    has_mention = False
    
    # Check for @ symbol or t.me/ in text
    if "@" in text or "t.me/" in text.lower():
        has_mention = True
        logger.debug(f"_check_and_process_thanks: found @ or t.me/ in text: '{text}'")
    
    # Check for mention entities (even without @ in text)
    if message.entities:
        entity_types = [e.type for e in message.entities]
        logger.debug(f"_check_and_process_thanks: message entities: {entity_types}")
        for entity in message.entities:
            if entity.type in ('text_mention', 'mention'):
                has_mention = True
                logger.info(f"_check_and_process_thanks: found {entity.type} entity in message '{text}'")
                break
    
    if has_mention:
        try:
            is_allowed = _is_allowed_topic(message, "THANKS_TOPIC_ID")
            logger.info(f"_check_and_process_thanks: has_mention={has_mention}, is_allowed={is_allowed}, text='{text}'")
            
            if is_allowed:
                user_language = await get_user_language(db_pool, message.from_user.id)
                logger.info(f"_check_and_process_thanks: calling handle_thanks_text for message '{text}'")
                await handle_thanks_text(message, db_pool, user_language, bot)
                return True
            else:
                logger.debug(f"_check_and_process_thanks: message not allowed in topic, text='{text}'")
        except Exception as e:
            logger.error(f"Error handling thanks text: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.debug(f"_check_and_process_thanks: no mention found in message '{text}'")
    return False

# --- Topic gating helper ---
def _is_allowed_topic(message: Message, allowed_topic_id_env: str) -> bool:
    """Return True if the message is in the allowed topic (by env), or if not applicable.

    Rules:
    - If chat is not a group/supergroup, allow (no topics in DMs).
    - If env var is missing/empty, allow (no restriction configured).
    - If chat is a topic-enabled supergroup/group, only allow when message_thread_id matches env var.
    """
    try:
        if message.chat.type not in ["group", "supergroup"]:
            return True
        allowed = os.getenv(allowed_topic_id_env)
        if not allowed:
            return True
        topic_id = getattr(message, "message_thread_id", None)
        result = topic_id is not None and str(topic_id) == str(allowed)
        return result
    except Exception as e:
        logger.error(f"Error checking topic: {e}")
        import traceback
        traceback.print_exc()
        # Fail-open: do not block if we cannot determine
        return True


async def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set")

    db_pool = await create_db_pool()
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    session = AiohttpSession(timeout=120.0)
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher()
    
    # Set up bot commands menu
    await setup_bot_commands(bot)
    
    # Initialize throttling, match system, followup system, username cache, scheduler, and feedback notification
    init_throttling(bot)
    init_match_system(bot, db_pool)
    init_followup_system(bot, db_pool)
    init_username_cache(bot, db_pool)
    init_scheduler(bot, db_pool)
    
    # Initialize bug reporting system
    init_bug_reporting(db_pool)
    
    # Check critical configuration and report issues
    await check_critical_configuration(db_pool)
    
    # Initialize feedback notification system
    admin_user_id = os.getenv("FEEDBACK_USER_ID")
    if admin_user_id:
        try:
            init_feedback_notification(bot, int(admin_user_id))
        except ValueError:
            logger.warning("Invalid FEEDBACK_USER_ID, feedback notifications disabled")
    else:
        logger.warning("FEEDBACK_USER_ID not set, feedback notifications disabled")
    
    # Add middleware
    dp.message.middleware(NoBotsMiddleware())
    dp.message.middleware(UpdateUserInteractionMiddleware(db_pool=db_pool))
    
    # Add DM-only commands middleware FIRST (before scene blocking)
    # Allow configuration via environment variable
    dm_only_commands_env = os.getenv("DM_ONLY_COMMANDS", 
        "start,edit_profile,view_profile,my_matches,browse,people,report_an_issue,suggest_a_feature,say,confirm_match")
    dm_only_commands = set(cmd.strip() for cmd in dm_only_commands_env.split(","))
    dp.message.middleware(DMOnlyCommandsMiddleware(dm_only_commands))
    
    # Add scene blocking middleware AFTER DM-only check
    dp.message.middleware(BlockBotCommandsInSceneMiddleware())
    
    # Add group membership middleware if group ID is configured
    group_id = os.getenv("TELEGRAM_GROUP_ID")
    if group_id:
        dp.message.middleware(GroupMembershipMiddleware(group_id))

    # Handle bot being added to group - multiple approaches
    @dp.my_chat_member()
    async def handle_bot_chat_member_update(event: ChatMemberUpdated):
        """Handle when bot's chat member status changes"""
        try:
            chat_id = event.chat.id
            chat_type = event.chat.type
            old_status = event.old_chat_member.status
            new_status = event.new_chat_member.status
            
            logger.info(f"🤖 Bot status changed in {chat_type} chat {chat_id}: {old_status} -> {new_status}")
            
            # Check if bot was added to group (from left/kicked to member/admin)
            if (old_status in [LEFT, KICKED] and 
                new_status in [MEMBER, ADMINISTRATOR, CREATOR] and 
                chat_type in ["group", "supergroup"]):
                
                logger.info(f"🎉 Bot added to {chat_type} chat {chat_id}")
                
                # Try to detect language from chat title or use default
                chat_title = getattr(event.chat, 'title', '')
                user_language = "en" if any(word in chat_title.lower() for word in ["english", "eng", "en"]) else "ru"
                
                # Send welcome message
                await send_welcome_message(bot, chat_id, user_language)
                
                # Also try to set commands for this specific group
                try:
                    group_commands = get_commands_for_chat_type("group", user_language)
                    await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=chat_id))
                    logger.info(f"✅ Commands set for group {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Error setting commands for group {chat_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling bot chat member update: {e}")

    # Handle system messages about bot being added
    @dp.message(F.new_chat_members)
    async def handle_new_chat_members(message: Message):
        """Handle when new members (including bot) are added to chat"""
        try:
            chat_id = message.chat.id
            chat_type = message.chat.type
            
            logger.info(f"🔍 New chat members event in {chat_type} chat {chat_id}")
            logger.info(f"🔍 New members: {[member.id for member in message.new_chat_members]}")
            
            # Check if bot was added to the group
            bot_info = await bot.get_me()
            logger.info(f"🔍 Bot ID: {bot_info.id}")
            
            bot_was_added = any(member.id == bot_info.id for member in message.new_chat_members)
            logger.info(f"🔍 Bot was added: {bot_was_added}")
            
            if bot_was_added and chat_type in ["group", "supergroup"]:
                logger.info(f"🎉 Bot detected being added to {chat_type} chat {chat_id} via new_chat_members")
                
                # Try to detect language from chat title or use default
                chat_title = getattr(message.chat, 'title', '')
                user_language = "en" if any(word in chat_title.lower() for word in ["english", "eng", "en"]) else "ru"
                
                # Send welcome message
                await send_welcome_message(bot, chat_id, user_language)
                
                # Also try to set commands for this specific group
                try:
                    group_commands = get_commands_for_chat_type("group", user_language)
                    await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=chat_id))
                    logger.info(f"✅ Commands set for group {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Error setting commands for group {chat_id}: {e}")
            else:
                logger.info(f"🔍 Not sending welcome: bot_was_added={bot_was_added}, chat_type={chat_type}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling new chat members: {e}")

    @dp.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext):
        print(f"DEBUG: Start command handler called for user {message.from_user.id}")
        print(f"DEBUG: Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
        # Check if user already has a complete profile
        user_id = message.from_user.id
        
        # First, check if user exists by Telegram user_id
        user_info = await get_user_info(db_pool, user_id)
        
        # If not found by user_id, check if user exists by username (for frontend-created users)
        if not user_info and message.from_user.username:
            async with db_pool.acquire() as conn:
                # Look for user with matching username and negative user_id (temporary)
                existing_user = await conn.fetchrow(
                    "SELECT user_id, user_telegram_link FROM users WHERE user_telegram_link = $1 AND user_id < 0",
                    message.from_user.username
                )
                
                if existing_user:
                    print(f"DEBUG: Found frontend-created user with temporary ID {existing_user['user_id']}, updating to {user_id}")
                    # Update the user_id to the actual Telegram user_id, preserving finishedonboarding and state
                    finishedonboarding_value = existing_user.get('finishedonboarding', True)
                    state_value = existing_user.get('state', 'ACTIVE')
                    await conn.execute(
                        "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                        user_id, existing_user['user_id'], finishedonboarding_value, state_value
                    )
                    print(f"DEBUG: Updated user_id to {user_id}, preserved finishedonboarding={finishedonboarding_value}, state={state_value}")
                    # Now get the updated user info
                    user_info = await get_user_info(db_pool, user_id)
        
        if user_info:
            # Check if user has required fields (name and description >= 10 chars)
            # If yes, auto-enable finishedonboarding even if admin disabled it
            async with db_pool.acquire() as conn:
                user_check = await conn.fetchrow(
                    """
                    SELECT 
                        intro_name,
                        intro_description,
                        finishedonboarding,
                        state
                    FROM public.users 
                    WHERE user_id = $1
                    """,
                    user_id
                )
                if user_check:
                    has_name = user_check['intro_name'] and len(user_check['intro_name'].strip()) > 0
                    has_description = user_check['intro_description'] and len(user_check['intro_description'].strip()) >= 10
                    
                    # Auto-enable finishedonboarding if user has required fields but it's disabled
                    if has_name and has_description and not user_check['finishedonboarding']:
                        await conn.execute(
                            "UPDATE public.users SET finishedonboarding = true, updated_at = now() WHERE user_id = $1",
                            user_id
                        )
                        print(f"DEBUG: Auto-enabled finishedonboarding=true for user {user_id} in /start (has required fields)")
                        # Refresh user_info after update
                        user_info = await get_user_info(db_pool, user_id)
                    
                    # Also ensure state is ACTIVE if it's not
                    if user_check['state'] != 'ACTIVE':
                        await conn.execute(
                            "UPDATE public.users SET state = 'ACTIVE', updated_at = now() WHERE user_id = $1",
                            user_id
                        )
                        print(f"DEBUG: Auto-set state='ACTIVE' for user {user_id} in /start")
            
            # User has profile - show it and offer editing
            from scenes import get_messages_dynamic, build_profile_text, get_edit_profile_keyboard
            
            # Send profile info message first
            await message.answer("У вас уже есть профиль:")
            
            # Send photo if available
            if user_info.get("intro_image"):
                try:
                    import base64
                    from aiogram.types import BufferedInputFile
                    
                    photo_data = base64.b64decode(user_info["intro_image"])
                    input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                    await message.answer_photo(input_file)
                except Exception as photo_error:
                    print(f"DEBUG: Error sending photo: {photo_error}")
            
            # Load existing data into session for editing
            await state.update_data(
                name=user_info.get("intro_name"),
                location=user_info.get("intro_location"),
                description=user_info.get("intro_description"),
                linkedin=user_info.get("intro_linkedin"),
                hobbies_drivers=user_info.get("intro_hobbies_drivers"),
                skills=user_info.get("intro_skills"),
                field_of_activity=user_info.get("field_of_activity"),
                birthday=user_info.get("intro_birthday"),
                photo_base64=user_info.get("intro_image")
            )
            
            # Show profile with editing options
            messages = get_messages_dynamic(user_id)
            profile_text = build_profile_text(user_info, user_id, is_own_profile=True)
            profile_text += f"\n\n{messages['ONBOARDING']['PROFILE']['ASK_ANY_CHANGES']}"
            
            keyboard = get_edit_profile_keyboard()
            await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")
            await state.set_state(ProfileStates.editing_profile)
        else:
            # User has no profile - start onboarding
            await start_onboarding(message, state, db_pool)


    @dp.message(Command("hello"))
    async def handle_hello(message: Message):
        """Simple test command"""
        try:
            logger.info(f"👋 hello command received from user {message.from_user.id}")
            await message.answer("👋 Hello! This is a test command. If you see this, commands are working!")
        except Exception as e:
            logger.error(f"❌ Error in hello command: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("refresh_menu"))
    async def handle_refresh_menu(message: Message):
        """Handle /refresh_menu command to manually refresh bot commands"""
        try:
            await setup_bot_commands(bot)
            await message.answer("✅ Menu commands refreshed successfully!")
        except Exception as e:
            await message.answer(f"❌ Ошибка обновления меню: {e}")

    @dp.message(Command("check_menu"))
    async def handle_check_menu(message: Message):
        """Handle /check_menu command to check current bot commands"""
        try:
            from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
            
            # Check commands for different scopes
            default_commands = await bot.get_my_commands(scope=BotCommandScopeDefault())
            group_commands = await bot.get_my_commands(scope=BotCommandScopeAllGroupChats())
            private_commands = await bot.get_my_commands(scope=BotCommandScopeAllPrivateChats())
            
            response = f"📋 <b>Current Bot Commands:</b>\n\n"
            response += f"🔹 <b>Default Scope:</b> {len(default_commands)} commands\n"
            response += f"🔹 <b>Group Scope:</b> {len(group_commands)} commands\n"
            response += f"🔹 <b>Private Scope:</b> {len(private_commands)} commands\n\n"
            response += f"💬 <b>Current Chat:</b> {message.chat.type} (ID: {message.chat.id})\n"
            
            if group_commands:
                response += f"\n📝 <b>Group Commands:</b>\n"
                for cmd in group_commands[:5]:  # Show first 5
                    response += f"• {cmd.description} → /{cmd.command}\n"
            
            await message.answer(response)
        except Exception as e:
            await message.answer(f"❌ Ошибка проверки меню: {e}")

    @dp.message(Command("set_group_menu"))
    async def handle_set_group_menu(message: Message):
        """Handle /set_group_menu command to set commands for current group"""
        try:
            if message.chat.type in ["group", "supergroup"]:
                # Set commands for this specific group - same as private chats
                group_commands = get_commands_for_chat_type("group", "ru")
                
                # Try multiple methods for this specific group
                await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=message.chat.id))
                await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
                await bot.set_my_commands(commands)
                
                await message.answer(f"✅ Menu commands set for this group (ID: {message.chat.id}) using multiple methods!")
            else:
                await message.answer("❌ Эта команда работает только в групповых чатах.")
        except Exception as e:
            await message.answer(f"❌ Ошибка настройки группового меню: {e}")

    @dp.message(Command("force_menu"))
    async def handle_force_menu(message: Message):
        """Handle /force_menu command to force menu setup"""
        try:
            # Force setup bot commands
            await setup_bot_commands(bot)
            
            # Also try to set for current chat if it's a group
            if message.chat.type in ["group", "supergroup"]:
                group_commands = get_commands_for_chat_type("group", "ru")
                await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=message.chat.id))
            
            await message.answer("✅ Меню принудительно обновлено! Пожалуйста, перезапустите приложение Telegram и проверьте кнопку меню (☰).")
        except Exception as e:
            await message.answer(f"❌ Ошибка принудительного обновления меню: {e}")

    @dp.message(Command("refresh_menu"))
    async def handle_refresh_menu(message: Message):
        """Handle /refresh_menu command to refresh bot menu"""
        try:
            await setup_bot_commands(bot)
            await message.answer("✅ Bot menu refreshed! The new menu should appear in your Telegram app.")
        except Exception as e:
            await message.answer(f"❌ Ошибка обновления меню: {e}")

    @dp.message(Command("set_dynamic_menu"))
    async def handle_set_dynamic_menu(message: Message):
        """Handle /set_dynamic_menu command to set dynamic menu for current chat"""
        try:
            # Get user language
            try:
                user_language = await get_user_language(db_pool, message.from_user.id)
            except:
                user_language = "ru"
            
            if message.chat.type == "private":
                # Set private chat commands
                private_commands = get_commands_for_chat_type("private", user_language)
                await bot.set_my_commands(private_commands, scope=BotCommandScopeChat(chat_id=message.chat.id))
                await message.answer(
                    f"✅ <b>Динамическое меню установлено для личного чата!</b>\n\n"
                    f"Доступные команды:\n"
                    f"• /start - Начать регистрацию\n"
                    f"• /edit_profile - Изменить профиль\n"
                    f"• /view_profile - Просмотреть профиль\n"
                    f"• /my_matches - Мои контакты\n"
                    f"• /browse - Список резидентов\n"
                    f"• /report_an_issue - Сообщить о проблеме\n"
                    f"• /suggest_a_feature - Предложить функцию\n"
                    f"• /say - Спросить ChatGPT\n"
                    f"• /cancel - Отменить действие\n"
                    f"• /help - Помощь\n\n"
                    f"💡 Все команды доступны в личном чате!"
                )
            elif message.chat.type in ["group", "supergroup"]:
                # Set group chat commands
                group_commands = get_commands_for_chat_type("group", user_language)
                await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=message.chat.id))
                await message.answer(
                    f"✅ <b>Динамическое меню установлено для группового чата!</b>\n\n"
                    f"Доступные команды:\n"
                    f"• /say - Спросить ChatGPT\n"
                    f"• /cancel - Отменить действие\n"
                    f"• /help - Помощь\n\n"
                    f"💡 Для полного доступа к командам используйте бота в личных сообщениях!"
                )
            else:
                await message.answer("❌ Неподдерживаемый тип чата для динамического меню.")
                
        except Exception as e:
            await message.answer(f"❌ Ошибка установки динамического меню: {e}")

    @dp.message(Command("botfather_commands"))
    async def handle_botfather_commands(message: Message):
        """Handle /botfather_commands to show BotFather command setup"""
        botfather_commands = """
🤖 <b>BotFather Command Setup</b>

Since the menu button isn't appearing in groups, you can set it up manually using BotFather:

1. Open @BotFather in Telegram
2. Send: <code>/setcommands</code>
3. Select your bot: <code>@KryloxBot</code>
4. Send these commands:

<code>start - 🚀 Начать регистрацию
view_profile - 👤 Просмотреть свой профиль
edit_profile - ✏️ Изменить свой профиль
my_matches - 💕 Смотреть мои пары
people - 🔍 Смотреть всех пользователей
confirm_match - ✅ Подтвердить пары
thanks - 🙏 Благодарности
stats - 📊 Статистика
top - 🏆 Топ пользователей
report_an_issue - 🐛 Сообщить о проблеме
suggest_a_feature - 💡 Предложить функцию
help - ❓ Помощь</code>

5. After setting, restart Telegram and check for menu button (☰)

<b>Alternative:</b> Use <code>/menu</code> command for inline keyboard menu.
        """
        await message.answer(botfather_commands)

    @dp.message(Command("diagnose_menu"))
    async def handle_diagnose_menu(message: Message):
        """Handle /diagnose_menu command to diagnose menu button issues"""
        try:
            # Get bot info
            bot_info = await bot.get_me()
            
            # Get chat info
            chat_info = await bot.get_chat(message.chat.id)
            
            # Get bot member info in this chat
            try:
                bot_member = await bot.get_chat_member(message.chat.id, bot_info.id)
                bot_status = bot_member.status
                bot_can_read = True
            except Exception:
                bot_status = "unknown"
                bot_can_read = False
            
            # Check if bot is admin
            is_admin = bot_status in ["creator", "administrator"]
            
            response = f"""
🔍 <b>Menu Button Diagnosis</b>

<b>Bot Information:</b>
• Name: @{bot_info.username}
• ID: {bot_info.id}
• Can Join Groups: {bot_info.can_join_groups}
• Can Read All Group Messages: {bot_info.can_read_all_group_messages}

<b>Chat Information:</b>
• Type: {chat_info.type}
• ID: {chat_info.id}
• Title: {chat_info.title}

<b>Bot Status in Chat:</b>
• Status: {bot_status}
• Is Admin: {is_admin}
• Can Read Messages: {bot_can_read}

<b>Possible Issues:</b>
• Menu button may not appear in channels
• Bot might need admin rights in some groups
• Telegram client version might be outdated
• Group type might not support menu buttons

<b>Solutions to Try:</b>
1. Make bot admin in the group
2. Try in a different group type (supergroup vs group)
3. Update Telegram app
4. Use BotFather to set commands manually
            """
            
            await message.answer(response)
        except Exception as e:
            await message.answer(f"❌ Ошибка диагностики меню: {e}")

    @dp.message(Command("topic_id"))
    async def handle_topic_id(message: Message):
        """Debug: print current message_thread_id and chat info"""
        thread_id = getattr(message, "message_thread_id", None)
        await message.answer(
            f"chat_id={message.chat.id}\nchat_type={message.chat.type}\nmessage_thread_id={thread_id}"
        )

    @dp.message(Command("test_menu_button"))
    async def handle_test_menu_button(message: Message):
        """Handle /test_menu_button to test different menu setups"""
        try:
            # Try setting commands with different methods - same as private chats
            commands = [
                BotCommand(command="start", description="Начать регистрацию"),
                BotCommand(command="edit_profile", description="Изменить свой профиль"),
                BotCommand(command="view_profile", description="Просмотреть свой профиль"),
                BotCommand(command="report_an_issue", description="Сообщить о проблеме"),
                BotCommand(command="suggest_a_feature", description="Предложить функцию"),
                BotCommand(command="my_matches", description="Мои контакты"),
                BotCommand(command="browse", description="Список резидентов"),
                BotCommand(command="thanks", description="Благодарности"),
                BotCommand(command="stats", description="Статистика"),
                BotCommand(command="top", description="Топ пользователей"),
                BotCommand(command="help", description="Помощь"),
            ]
            
            # Try multiple setup methods
            await bot.set_my_commands(group_commands, scope=BotCommandScopeChat(chat_id=message.chat.id))
            await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
            await bot.set_my_commands(group_commands)
            
            await message.answer("""
✅ <b>Menu Button Test Complete</b>

I've tried multiple methods to set up the menu button:

1. ✅ Set commands for this specific group
2. ✅ Set commands for all group chats  
3. ✅ Set commands globally

<b>Next Steps:</b>
1. <b>Close Telegram completely</b> (not just minimize)
2. <b>Reopen Telegram</b>
3. <b>Go to your group chat</b>
4. <b>Look for menu button (☰)</b> next to text input

<b>If still no menu button:</b>
• Try in a regular group (not supergroup)
• Use BotFather method: @BotFather → /setcommands
• Update Telegram app
• Try different Telegram client (mobile/desktop)

<b>Note:</b> Some supergroups don't show menu buttons due to Telegram limitations.
            """)
        except Exception as e:
            await message.answer(f"❌ Ошибка тестирования кнопки меню: {e}")

    

    @dp.message(Command("cancel"))
    async def handle_cancel(message: Message, state: FSMContext):
        """Handle /cancel command to exit current scene"""
        from scenes import get_messages_dynamic
        
        current_state = await state.get_state()
        messages = get_messages_dynamic(message.from_user.id)
        
        if current_state and current_state != "default":
            await state.clear()
            await message.answer(messages["CANCEL"]["ACTION_CANCELLED"])
        else:
            await message.answer(messages["CANCEL"]["NO_ACTION"])

    @dp.message(F.text.in_([
        "Continue where I left off", "Start over", "Cancel and exit",
        "Продолжить с того места", "Начать заново", "Отменить и выйти"
    ]))
    async def handle_progress_decision(message: Message, state: FSMContext):
        """Handle user decision about incomplete action"""
        current_state = await state.get_state()
        
        if message.text in ["Continue where I left off", "Продолжить с того места"]:
            # Continue with current state - just send a message
            await message.answer("Продолжаем с того места, где остановились. Пожалуйста, завершите текущий шаг.")
            
        elif message.text in ["Start over", "Начать заново"]:
            # Clear state and start fresh onboarding
            await state.clear()
            await start_onboarding(message, state, db_pool)
            
        elif message.text in ["Cancel and exit", "Отменить и выйти"]:
            # Clear state and show menu
            await state.clear()
            await message.answer("Действие отменено. Теперь вы можете использовать любую команду.")

    @dp.message(Command("help"))
    async def handle_help(message: Message):
        """Handle /help command - context-aware help based on chat type and topic"""
        # Use bot language from environment variable instead of user language
        bot_language = os.getenv("BOT_LANGUAGE", "ru")  # Default to Russian
        print(f"DEBUG: Help command - bot_language: '{bot_language}' for user {message.from_user.id}, chat type: {message.chat.type}")
        print(f"DEBUG: Message thread ID: {getattr(message, 'message_thread_id', 'None')}")
        print(f"DEBUG: Chat ID: {message.chat.id}")
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(bot_language)
        
        # Check if we're in a private chat (DM)
        if message.chat.type == "private":
            print(f"DEBUG: Help command in private chat, showing DM help")
            # Show full help for DM
            await _show_dm_help(message, messages, bot_language)
        else:
            print(f"DEBUG: Help command in {message.chat.type} chat, showing topic help")
            # Show topic-specific help for groups/topics
            await _show_topic_help(message, messages, bot_language)

    async def _show_dm_help(message: Message, messages, bot_language: str):
        """Show full help for DM users"""
        # Define command descriptions based on language
        if bot_language == "en":
            print(f"DEBUG: Using English command descriptions for DM")
            command_descriptions = {
                "start": "Start the bot and begin onboarding",
                "help": "Show help and available commands", 
                "view_profile": "View your current profile",
                "edit_profile": "Edit your profile information",
                "my_matches": "View your top matches",
                "browse": "Browse other users",
                "confirm_match": "Confirm pending matches",
                "say": "Ask ChatGPT a question",
                "report_an_issue": "Report a bug or issue",
                "suggest_a_feature": "Suggest a new feature"
            }
        else:  # Russian (default)
            print(f"DEBUG: Using Russian command descriptions for DM")
            command_descriptions = {
                "start": "Начать работу с ботом и регистрацию",
                "help": "Показать помощь и доступные команды",
                "view_profile": "Ваш профиль", 
                "edit_profile": "Изменить информацию профиля",
                "my_matches": "Ваши мэтчи (random coffee)",
                "browse": "Список резидентов",
                "confirm_match": "Подтвердить ожидающие совпадения",
                "enable_matches": "Включить рекомендации встреч обратно",
                "say": "Спросить ChatGPT",
                "report_an_issue": "Сообщить об ошибке или проблеме",
                "suggest_a_feature": "Предложи изменение"
            }
        
        help_text = f"""
🤖 <b>{messages['COMMANDS']['BOT_UP']}</b>

<b>📋 {messages['COMMANDS']['HELP_TITLE']} (Личные сообщения)</b>

🚀 <b>/start</b> - {command_descriptions['start']}
❓ <b>/help</b> - {command_descriptions['help']}
👔 <b>/view_profile</b> - {command_descriptions['view_profile']}
✏️ <b>/edit_profile</b> - {command_descriptions['edit_profile']}
☕ <b>/my_matches</b> - {command_descriptions['my_matches']}
🏢 <b>/browse</b> - {command_descriptions['browse']}
✅ <b>/confirm_match</b> - {command_descriptions['confirm_match']}
🔄 <b>/enable_matches</b> - {command_descriptions['enable_matches']}
🤖 <b>/say</b> - {command_descriptions['say']}
🐛 <b>/report_an_issue</b> - {command_descriptions['report_an_issue']}
💡 <b>/suggest_a_feature</b> - {command_descriptions['suggest_a_feature']}

<b>🎯 Команды для топиков:</b>

<b>Команды благодарностей (для топика Thanks):</b>
🙏 <b>/thanks @username</b> - Поблагодарить пользователя
📊 <b>/stats</b> - Посмотреть полную статистику благодарностей
🏆 <b>/top [N]</b> - Посмотреть топ N самых благодарных пользователей

<b>💡 {messages['COMMANDS']['HELP_TIP']}</b>

<b>📞 {messages['COMMANDS']['HELP_SUPPORT']}</b>
        """
        
        # Help command should just show information, no keyboard needed
        # Explicitly remove any existing keyboard
        from aiogram.types import ReplyKeyboardRemove
        await message.answer(help_text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

    async def _show_topic_help(message: Message, messages, bot_language: str):
        """Show topic-specific help for group/topic users"""
        print(f"DEBUG: _show_topic_help called for chat type: {message.chat.type}")
        # Check which topic we're in
        is_thanks_topic = _is_allowed_topic(message, "THANKS_TOPIC_ID")
        is_birthday_topic = _is_allowed_topic(message, "BIRTHDAY_TOPIC_ID")
        print(f"DEBUG: is_thanks_topic: {is_thanks_topic}, is_birthday_topic: {is_birthday_topic}")
        print(f"DEBUG: THANKS_TOPIC_ID env: {os.getenv('THANKS_TOPIC_ID', 'Not set')}")
        print(f"DEBUG: BIRTHDAY_TOPIC_ID env: {os.getenv('BIRTHDAY_TOPIC_ID', 'Not set')}")
        
        if bot_language == "en":
            print(f"DEBUG: Using English command descriptions for topic")
            command_descriptions = {
                "help": "Show help and available commands",
                "thanks": "Thank someone or view thanks stats",
                "stats": "View your thanks statistics", 
                "top": "View top thanked users",
                "check_birthdays": "Check today's birthdays"
            }
        else:  # Russian (default)
            print(f"DEBUG: Using Russian command descriptions for topic")
            command_descriptions = {
                "help": "Показать помощь и доступные команды",
                "thanks": "Поблагодарить кого-то или посмотреть статистику благодарностей",
                "stats": "Просмотреть вашу статистику благодарностей",
                "top": "Просмотреть самых благодаренных пользователей", 
                "check_birthdays": "Проверить дни рождения сегодня"
            }
        
        if is_thanks_topic:
            help_text = f"""
🤖 <b>{messages['COMMANDS']['BOT_UP']}</b>

<b>📋 {messages['COMMANDS']['HELP_TITLE']} (Тема благодарностей)</b>

❓ <b>/help</b> - {command_descriptions['help']}
🙏 <b>/thanks</b> - {command_descriptions['thanks']}
📊 <b>/stats</b> - {command_descriptions['stats']}
🏆 <b>/top</b> - {command_descriptions['top']}

<b>💡 Используйте эти команды для работы с благодарностями</b>
            """
        elif is_birthday_topic:
            help_text = f"""
🤖 <b>{messages['COMMANDS']['BOT_UP']}</b>

🎂 <b>Добро пожаловать в тему дней рождения!</b>

Этот топик предназначен для информирования о днях рождения участников сообщества. Здесь вы будете получать уведомления о предстоящих и текущих днях рождения ваших коллег.

<b>💡 Для полного функционала бота напишите ему в личные сообщения</b>
            """
        else:
            # Generic group help
            help_text = f"""
🤖 <b>{messages['COMMANDS']['BOT_UP']}</b>

<b>📋 {messages['COMMANDS']['HELP_TITLE']} (Группа)</b>

❓ <b>/help</b> - {command_descriptions['help']}

<b>💡 Для полного функционала напишите боту в личные сообщения</b>
            """
        
        await message.answer(help_text)

    @dp.message(Command("edit_profile"))
    async def handle_edit_profile_command(message: Message, state: FSMContext):
        await handle_edit_profile(message, state, db_pool)

    @dp.message(Command("view_profile"))
    async def handle_view_profile_command(message: Message, state: FSMContext):
        await handle_view_profile(message, state, db_pool)

    @dp.message(Command("report_an_issue"))
    async def handle_report_issue(message: Message, state: FSMContext):
        await state.set_data({"feedback_type": "issue"})
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        
        from scenes import get_exit_keyboard
        keyboard = get_exit_keyboard()
        await message.answer(
            f"🐛 <b>{messages['COMMANDS']['FEEDBACK_REPORT_ISSUE']}</b>\n\n"
            f"{messages['COMMANDS']['FEEDBACK_DESCRIBE_ISSUE']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_WHAT_TRYING']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_WHAT_HAPPENED']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_ERROR_MESSAGES']}\n\n"
            f"{messages['COMMANDS']['FEEDBACK_HELPS_IMPROVE']}",
            reply_markup=keyboard
        )

    @dp.message(Command("suggest_a_feature"))
    async def handle_suggest_feature(message: Message, state: FSMContext):
        logger.info(f"handle_suggest_feature: Setting feedback_type='feature' for user {message.from_user.id}")
        await state.set_data({"feedback_type": "feature"})
        # Verify state was set
        verify_data = await state.get_data()
        logger.info(f"handle_suggest_feature: State data after setting: {verify_data}, feedback_type={verify_data.get('feedback_type')}")
        
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        
        from scenes import get_exit_keyboard
        keyboard = get_exit_keyboard()
        await message.answer(
            f"💡 <b>{messages['COMMANDS']['FEEDBACK_SUGGEST_FEATURE']}</b>\n\n"
            f"{messages['COMMANDS']['FEEDBACK_DESCRIBE_IDEA']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_FEATURE_DETAILS']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_HOW_HELP']}\n"
            f"• {messages['COMMANDS']['FEEDBACK_SPECIFIC_DETAILS']}\n\n"
            f"{messages['COMMANDS']['FEEDBACK_HELP_MAKE_BETTER']}",
            reply_markup=keyboard
        )

    @dp.message(Command("my_matches"))
    async def handle_my_matches(message: Message, state: FSMContext):
        """Handle my_matches command with inline buttons"""
        print(f"DEBUG: my_matches command received from user {message.from_user.id}")
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        user_id = message.from_user.id
        
        # First, check if user exists by Telegram user_id
        # Also check for admin-created users with temporary negative user_id
        async with db_pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT matches_disabled, finishedonboarding, state FROM users WHERE user_id = $1",
                user_id
            )
            
            # If not found by user_id, check if user exists by username (for frontend-created users)
            if not user_row and message.from_user.username:
                existing_user = await conn.fetchrow(
                    "SELECT user_id, finishedonboarding, state, matches_disabled FROM users WHERE user_telegram_link = $1 AND user_id < 0",
                    message.from_user.username
                )
                
                if existing_user:
                    print(f"DEBUG: Found frontend-created user with temporary ID {existing_user['user_id']}, updating to {user_id}")
                    # Update the user_id to the actual Telegram user_id, preserving finishedonboarding and state
                    finishedonboarding_value = existing_user.get('finishedonboarding', True)
                    state_value = existing_user.get('state', 'ACTIVE')
                    await conn.execute(
                        "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                        user_id, existing_user['user_id'], finishedonboarding_value, state_value
                    )
                    print(f"DEBUG: Updated user_id to {user_id}, preserved finishedonboarding={finishedonboarding_value}, state={state_value}")
                    # Now get the updated user info
                    user_row = await conn.fetchrow(
                        "SELECT matches_disabled, finishedonboarding, state FROM users WHERE user_id = $1",
                        user_id
                    )
            
            if not user_row:
                await message.answer(messages["COMMANDS"]["COMPLETE_ONBOARDING"])
                return
            
            # Check if matches are disabled
            if user_row['matches_disabled']:
                user_lang = await get_user_language(db_pool, user_id)
                if user_lang == 'ru':
                    await message.answer(
                        "Рекомендации встреч временно отключены для вашего профиля.\n\n"
                        "Вы можете включить их снова, используя кнопку \"Включить рекомендации\" в сообщении с рекомендацией или команду /enable_matches.\n\n"
                        "Также вы можете обратиться к администратору для изменения этого статуса."
                    )
                else:
                    await message.answer(
                        "Meeting recommendations are temporarily disabled for your profile.\n\n"
                        "You can re-enable them by using the \"Enable recommendations\" button in a recommendation message or the /enable_matches command.\n\n"
                        "You can also contact an administrator to change this status."
                    )
                return
            
            # Check if user has required fields (name and description >= 10 chars)
            # If yes, auto-enable finishedonboarding even if admin disabled it
            user_name = user_row.get('intro_name')
            user_description = user_row.get('intro_description')
            has_name = user_name and len(user_name.strip()) > 0
            has_description = user_description and len(user_description.strip()) >= 10
            
            # Auto-enable finishedonboarding if user has required fields but it's disabled
            finished_onboarding = bool(user_row['finishedonboarding']) if user_row['finishedonboarding'] is not None else False
            if has_name and has_description and not finished_onboarding:
                await conn.execute(
                    "UPDATE public.users SET finishedonboarding = true, updated_at = now() WHERE user_id = $1",
                    user_id
                )
                finished_onboarding = True
                print(f"DEBUG: Auto-enabled finishedonboarding=true for user {user_id} in /my_matches (has required fields)")
            
            # Also ensure state is ACTIVE if it's not
            user_state = str(user_row['state']) if user_row['state'] else ''
            if user_state != 'ACTIVE':
                await conn.execute(
                    "UPDATE public.users SET state = 'ACTIVE', updated_at = now() WHERE user_id = $1",
                    user_id
                )
                user_state = 'ACTIVE'
                print(f"DEBUG: Auto-set state='ACTIVE' for user {user_id} in /my_matches")
            
            print(f"DEBUG: User {user_id} - finishedonboarding: {finished_onboarding} (type: {type(finished_onboarding)}), state: {user_state}")
            
            if not finished_onboarding or user_state != 'ACTIVE':
                print(f"DEBUG: User {user_id} failed onboarding check - finishedonboarding={finished_onboarding}, state={user_state}")
                # Check if user has required fields but they're missing something
                if not has_name or not has_description:
                    user_lang = await get_user_language(db_pool, user_id)
                    if user_lang == 'ru':
                        missing_fields = []
                        if not has_name:
                            missing_fields.append("имя")
                        if not has_description:
                            missing_fields.append("описание профиля (минимум 10 символов)")
                        await message.answer(
                            f"<b>Мои контакты</b>\n\n"
                            f"Для получения персональных рекомендаций встреч необходимо заполнить обязательные поля: {', '.join(missing_fields)}.\n\n"
                            f"📝 Используйте команду /edit_profile для редактирования профиля.",
                            parse_mode="HTML"
                        )
                    else:
                        missing_fields = []
                        if not has_name:
                            missing_fields.append("name")
                        if not has_description:
                            missing_fields.append("profile description (minimum 10 characters)")
                        await message.answer(
                            f"<b>My Contacts</b>\n\n"
                            f"To receive personalized meeting recommendations, please fill in required fields: {', '.join(missing_fields)}.\n\n"
                            f"📝 Use the /edit_profile command to edit your profile.",
                            parse_mode="HTML"
                        )
                else:
                    await message.answer(messages["COMMANDS"]["COMPLETE_ONBOARDING"])
                return
        
        # Get matchable users (for finding matches, but don't require the current user to be in this list)
        # The user might not have vector_description yet, which is OK for viewing their own matches
        users = await get_matchable_users(db_pool)
        if not users:
            await message.answer(messages["COMMANDS"]["NO_MATCHABLE_USERS"])
            return
        
        # Check if current user has vector_description (required for matching)
        # But don't block if they don't - they might still want to see matches
        async with db_pool.acquire() as conn:
            user_vector = await conn.fetchval(
                "SELECT vector_description FROM users WHERE user_id = $1",
                user_id
            )
        
        if user_vector is None:
            # User doesn't have vector_description - show the same message as for users without description
            # This handles both users with NULL vector and users with default vector but no description
            async with db_pool.acquire() as conn:
                user_description = await conn.fetchval(
                    "SELECT intro_description FROM users WHERE user_id = $1", user_id
                )
                has_real_description = user_description and len(user_description.strip()) >= 10
            
            user_lang = await get_user_language(db_pool, user_id)
            if user_lang == 'ru':
                await message.answer(
                    "<b>Мои контакты</b>\n\n"
                    "Для получения персональных рекомендаций встреч необходимо заполнить описание профиля.\n\n"
                    "📝 Добавьте описание о себе (минимум 10 символов), чтобы система могла подобрать вам подходящие контакты.\n\n"
                    "Используйте команду /edit_profile для редактирования профиля.",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "<b>My Contacts</b>\n\n"
                    "To receive personalized meeting recommendations, please fill in your profile description.\n\n"
                    "📝 Add a description about yourself (minimum 10 characters) so the system can find suitable contacts for you.\n\n"
                    "Use the /edit_profile command to edit your profile.",
                    parse_mode="HTML"
                )
            return
        
        # Get matches directly in main.py to avoid import issues
        from match_generation import cosine_similarity
        
        # First get users with vectors for similarity calculation
        users_with_vectors = await get_matchable_users(db_pool)
        print(f"DEBUG: Found {len(users_with_vectors)} total users with vectors")
        
        # Check if current user has real description (required for matching)
        async with db_pool.acquire() as conn:
            user_description = await conn.fetchval(
                "SELECT intro_description FROM users WHERE user_id = $1",
                user_id
            )
            has_real_description = user_description and len(user_description.strip()) >= 10
        
        target = next((u for u in users_with_vectors if u["user_id"] == message.from_user.id), None)
        print(f"DEBUG: Target user found: {target is not None}, has_real_description: {has_real_description}")
        
        if not target or not target.get("vector_description"):
            print(f"DEBUG: Target user has no vector_description or is not in matchable users. has_real_description: {has_real_description}")
            matches = []
            
            # Check if user has description but vector wasn't updated yet (e.g., after admin edit)
            if has_real_description:
                # User has description >= 10 chars but not in matchable users
                # This should NOT happen if vector was updated properly
                # Try to fix it immediately by regenerating the vector
                async with db_pool.acquire() as conn:
                    # Get current description from DB
                    current_description = await conn.fetchval(
                        "SELECT intro_description FROM users WHERE user_id = $1", user_id
                    )
                    existing_vector = await conn.fetchval(
                        "SELECT vector_description FROM users WHERE user_id = $1", user_id
                    )
                
                if current_description and len(current_description.strip()) >= 10:
                    # Description is valid - try to vectorize it NOW
                    try:
                        from vectorization import vectorize_description
                        from openai import AsyncOpenAI
                        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
                        
                        print(f"Fixing missing vector for user {user_id} - vectorizing description immediately")
                        new_vector = await vectorize_description(current_description.strip(), openai_client)
                        
                        if new_vector and len(new_vector) > 0:
                            async with db_pool.acquire() as conn:
                                await conn.execute(
                                    "UPDATE users SET vector_description = $1, updated_at = NOW() WHERE user_id = $2",
                                    new_vector, user_id
                                )
                            print(f"✓ Fixed: Regenerated vector for user {user_id}")
                            # Retry getting matches after vector was created
                            # Continue to normal matching flow below
                        else:
                            # Vectorization failed - use default vector so /my_matches works
                            from vectorization import create_default_vector
                            default_vector = await create_default_vector()
                            if default_vector:
                                async with db_pool.acquire() as conn:
                                    await conn.execute(
                                        "UPDATE users SET vector_description = $1, updated_at = NOW() WHERE user_id = $2",
                                        default_vector, user_id
                                    )
                                print(f"Created default vector for user {user_id} (vectorization failed)")
                    except Exception as fix_error:
                        print(f"❌ ERROR: Failed to fix vector for user {user_id}: {fix_error}")
                        import traceback
                        traceback.print_exc()
                
                # Show "no matches" message instead of confusing "wait" message
                user_lang = await get_user_language(db_pool, user_id)
                if user_lang == 'ru':
                    await message.answer(
                        "<b>Мои контакты</b>\n\n"
                        "К сожалению, сейчас нет доступных рекомендаций.\n\n"
                        "Попробуйте обновить описание профиля через /edit_profile или обратитесь к администратору.",
                        parse_mode="HTML"
                    )
                else:
                    await message.answer(
                        "<b>My Contacts</b>\n\n"
                        "Unfortunately, there are no available recommendations at the moment.\n\n"
                        "Try updating your profile description via /edit_profile or contact an administrator.",
                        parse_mode="HTML"
                    )
                return
            
            # User doesn't have real description
            user_lang = await get_user_language(db_pool, user_id)
            if user_lang == 'ru':
                await message.answer(
                    "<b>Мои контакты</b>\n\n"
                    "Для получения персональных рекомендаций встреч необходимо заполнить описание профиля.\n\n"
                    "📝 Добавьте описание о себе (минимум 10 символов), чтобы система могла подобрать вам подходящие контакты.\n\n"
                    "Используйте команду /edit_profile для редактирования профиля.",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "<b>My Contacts</b>\n\n"
                    "To receive personalized meeting recommendations, please fill in your profile description.\n\n"
                    "📝 Add a description about yourself (minimum 10 characters) so the system can find suitable contacts for you.\n\n"
                    "Use the /edit_profile command to edit your profile.",
                    parse_mode="HTML"
                )
            return
        else:
            scored = []
            for u in users_with_vectors:
                if u["user_id"] == target["user_id"]:
                    continue
                if not u.get("vector_description"):
                    continue
                score = cosine_similarity(target["vector_description"], u["vector_description"])
                scored.append((u["user_id"], score))
            
            print(f"DEBUG: Found {len(scored)} scored matches")
            scored.sort(key=lambda x: x[1], reverse=True)
            
            # Get full user data for top matches
            if scored:
                match_user_ids = [user_id for user_id, score in scored]
                async with db_pool.acquire() as connection:
                    rows = await connection.fetch(
                        """
                        select user_id, coalesce(intro_name, 'No name') as intro_name,
                               coalesce(intro_location, 'No location') as intro_location,
                               coalesce(intro_description, 'No description') as intro_description,
                               coalesce(intro_linkedin, 'No LinkedIn') as intro_linkedin,
                               intro_hobbies_drivers, intro_skills, field_of_activity, intro_birthday,
                               intro_image, user_telegram_link
                        from public.users
                        where user_id = ANY($1)
                        """,
                        match_user_ids
                    )
                matches = [dict(row) for row in rows]
            else:
                matches = []
        
        print(f"DEBUG: Found {len(matches)} matches for user {message.from_user.id}")
        
        if not matches:
            # Show professional placeholder for no matches
            await show_no_matches_placeholder(message, state)
            return
        
        # Show first match
        await state.set_state(MyMatchesStates.viewing_matches)
        await state.update_data(matches=matches, current_index=0)
        await show_match_profile(message, matches[0], 0, len(matches))

    async def show_match_profile(message: Message, user_info: dict, current_index: int, total_matches: int):
        """Show a match profile with text-based details"""
        from scenes import get_messages_dynamic, build_profile_text
        
        # Send photo first if available
        if user_info.get("intro_image"):
            print(f"DEBUG: Processing image data: {user_info['intro_image'][:100]}...")
            try:
                import base64
                import aiohttp
                from aiogram.types import BufferedInputFile
                
                image_data = user_info["intro_image"]
                print(f"DEBUG: Image data type: {type(image_data)}, length: {len(image_data) if image_data else 0}")
                
                # Handle different image formats
                if image_data.startswith('data:image/'):
                    print(f"DEBUG: Processing data URL format")
                    # Data URL format - extract base64 part
                    base64_data = image_data.split(',')[1]
                    photo_data = base64.b64decode(base64_data)
                elif image_data.startswith(('http://', 'https://')):
                    print(f"DEBUG: Processing URL format: {image_data}")
                    # URL format - download and convert to base64
                    
                    # Check if it's ui-avatars.com and modify URL to request PNG format
                    if 'ui-avatars.com' in image_data and 'format=' not in image_data:
                        image_data = image_data + '&format=png'
                        print(f"DEBUG: Modified URL to request PNG: {image_data}")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_data) as response:
                            if response.status == 200:
                                photo_data = await response.read()
                                content_type = response.headers.get('content-type', 'unknown')
                                print(f"DEBUG: Downloaded image data, size: {len(photo_data)} bytes")
                                print(f"DEBUG: Image content type: {content_type}")
                                
                                # Check if it's SVG and skip if so
                                if 'svg' in content_type.lower() or photo_data.startswith(b'<svg'):
                                    print(f"DEBUG: Skipping SVG image (not supported by Telegram)")
                                    return
                            else:
                                print(f"DEBUG: Failed to download image from URL: {response.status}")
                                return
                else:
                    print(f"DEBUG: Processing as raw base64 data")
                    # Assume it's raw base64 data
                    photo_data = base64.b64decode(image_data)
                
                print(f"DEBUG: About to send photo, data size: {len(photo_data)} bytes")
                input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                await message.answer_photo(input_file)
                print(f"DEBUG: Photo sent successfully")
            except Exception as photo_error:
                print(f"DEBUG: Error sending photo: {photo_error}")
                # Continue without photo if there's an error
        
        # Build profile text using new format
        profile_text = build_profile_text(user_info, message.from_user.id, is_own_profile=False)
        
        # Send text-only profile
        keyboard = await get_my_matches_keyboard(has_next=current_index < total_matches - 1)
        await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")


    async def show_no_matches_placeholder(message: Message, state: FSMContext):
        """Show text-based no matches message when user has description but no matches found"""
        # Create text-only no matches message
        # This is shown when user has real description but no matches were found
        from db import get_user_language
        user_lang = await get_user_language(db_pool, message.from_user.id)
        
        if user_lang == 'ru':
            placeholder_text = "<b>Мои контакты</b>\n\n"
            placeholder_text += "Пока нет рекомендаций встреч.\n\n"
            placeholder_text += "Попробуйте:\n"
            placeholder_text += "• Обновить описание профиля (/edit_profile)\n"
            placeholder_text += "• Посмотреть всех пользователей (кнопка ниже)"
        else:
            placeholder_text = "<b>My Contacts</b>\n\n"
            placeholder_text += "No meeting recommendations yet.\n\n"
            placeholder_text += "Try:\n"
            placeholder_text += "• Updating your profile description (/edit_profile)\n"
            placeholder_text += "• Browsing all users (button below)"
        
        keyboard = await get_my_matches_keyboard(has_next=False)
        await state.set_state(MyMatchesStates.viewing_matches)
        await state.update_data(matches=[], current_index=0)
        await message.answer(placeholder_text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message(Command("browse"))
    async def handle_browse(message: Message, state: FSMContext):
        """Handle /browse command - advanced interactive list with clickable profiles"""
        try:
            # Check if user is in DM (this should be a DM-only command for privacy)
            if message.chat.type != "private":
                await message.answer("🔒 This command is only available in private messages with the bot.")
                return
            
            await state.clear()
            
            # Get all users for listing with more details (same as frontend API)
            async with db_pool.acquire() as connection:
                rows = await connection.fetch(
                """
                select user_id, 
                       coalesce(intro_name, '') as intro_name,
                       coalesce(intro_location, '') as intro_location,
                       coalesce(intro_description, '') as intro_description,
                       coalesce(field_of_activity, '') as field_of_activity,
                       user_telegram_link
                from public.users
                where finishedonboarding = true
                and user_id != $1
                order by intro_name asc
                """,
                message.from_user.id
            )
            
            if not rows:
                await message.answer("📋 No users available to list yet.")
                return
            
            users = [dict(row) for row in rows]
            
            # Create advanced interactive list message
            list_message = "🔍 <b>Интерактивный список пользователей</b>\n"
            list_message += f"Показано: {len(users)} пользователей\n\n"
            list_message += "✨ <b>Особенности:</b>\n"
            list_message += "• Кликабельные профили с полной информацией\n"
            list_message += "• Фотографии профилей\n"
            list_message += "• Ссылки на Telegram и LinkedIn\n"
            list_message += "• Детальное описание и сфера деятельности\n\n"
            list_message += "Нажмите на пользователя для просмотра полного профиля:\n\n"
            
            keyboard_buttons = []
            
            # Get translated messages for consistency
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            missing_text = messages["MISSING_FIELD"]
            
            # Helper function to get translated value
            def get_translated_value(value, fallback=missing_text):
                if not value or value in ['Not specified', 'Not specifie', 'No description', 'No name', 'No location', 'No field of activity', 'No hobbies']:
                    return fallback
                return value
            
            for i, user in enumerate(users, 1):
                name = get_translated_value(user['intro_name'])
                location = get_translated_value(user['intro_location'])
                field_of_activity = get_translated_value(user['field_of_activity'])
                
                # Extract country from location
                country = location.split(',')[-1].strip() if ',' in location else location
                
                # Use field of activity directly
                sphere = field_of_activity
                
                # Create button text (limited to 64 chars for Telegram)
                if sphere == missing_text:
                    sphere_display = missing_text
                else:
                    sphere_display = sphere[:12]
                
                button_text = f"{i}. {name[:18]} | {sphere_display} | {country[:12]}"
                if len(button_text) > 60:
                    if sphere == missing_text:
                        sphere_display = missing_text
                    else:
                        sphere_display = sphere[:10]
                    button_text = f"{i}. {name[:15]} | {sphere_display} | {country[:10]}"
                
                # Add button for each user
                keyboard_buttons.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"browse_user_{user['user_id']}"
                )])
            
            # Add navigation and utility buttons
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_user_list")
            ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Закрыть", callback_data="close_user_list")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.answer(list_message, parse_mode="HTML", reply_markup=keyboard)
            
        except Exception as e:
            await message.answer(f"❌ Ошибка при получении списка пользователей: {e}")
            logger.error(f"Error in browse command: {e}")

    @dp.message(Command("people"))
    async def handle_people(message: Message, state: FSMContext):
        """Handle /people command - same interface as 'Все пользователи' button"""
        await state.clear()
        await state.set_state(BrowseStates.browsing_users)
        
        # Get all users for browsing (same logic as my_matches_browse)
        async with db_pool.acquire() as connection:
            rows = await connection.fetch(
                """
                select user_id, coalesce(intro_name, 'No name') as intro_name,
                       coalesce(intro_location, 'No location') as intro_location,
                       coalesce(intro_description, 'No description') as intro_description,
                       coalesce(intro_linkedin, 'No LinkedIn') as intro_linkedin,
                       intro_image, user_telegram_link, intro_hobbies_drivers, intro_skills, intro_birthday,
                       coalesce(field_of_activity, 'Not specified') as field_of_activity
                from public.users
                where finishedonboarding = true
                and user_id != $1
                order by intro_name
                """,
                message.from_user.id
            )
        
        if not rows:
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            await message.answer(messages["COMMANDS"]["BROWSE_NO_USERS"])
            return
        
        users = [dict(row) for row in rows]
        await state.update_data(browse_users=users, browse_index=0)
        await show_browse_profile(message, users[0], 0, len(users), state)

    @dp.message(Command("confirm_match"))
    async def handle_confirm_match(message: Message, state: FSMContext):
        """Handle manual match confirmation"""
        user_id = message.from_user.id
        
        # Get user's pending matches
        async with db_pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT m.id, m.user_1_id, m.user_2_id, m.status,
                       u1.intro_name as user1_name, u2.intro_name as user2_name
                FROM public.meetings m
                JOIN public.users u1 ON m.user_1_id = u1.user_id
                JOIN public.users u2 ON m.user_2_id = u2.user_id
                WHERE (m.user_1_id = $1 OR m.user_2_id = $1)
                  AND m.status = 'new'
                ORDER BY m.created_at DESC
                LIMIT 5
                """,
                user_id
            )
        
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        
        if not rows:
            await message.answer(messages["COMMANDS"]["NO_PENDING_MATCHES"])
            return
        
        # Display pending matches
        match_text = "🔍 <b>Your Pending Matches:</b>\n\n"
        for i, row in enumerate(rows, 1):
            other_user_id = row['user_2_id'] if row['user_1_id'] == user_id else row['user_1_id']
            other_user_name = row['user2_name'] if row['user_1_id'] == user_id else row['user1_name']
            
            match_text += f"{i}. <b>{other_user_name}</b> (ID: {other_user_id})\n"
            match_text += f"   Meeting ID: {row['id']}\n\n"
        
        match_text += "To confirm a match, reply with the meeting ID number."
        from scenes import get_exit_keyboard
        keyboard = get_exit_keyboard()
        await message.answer(match_text, reply_markup=keyboard)
        
        # Store the matches in user's state for confirmation
        await state.set_data({"pending_matches": [dict(row) for row in rows]})
        await state.set_state("waiting_for_match_confirmation")

    # Onboarding scene handlers
    @dp.message(StateFilter(OnboardingStates.waiting_for_name))
    async def handle_name_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_name(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_location))
    async def handle_location_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_location(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_description))
    async def handle_description_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_description(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_linkedin))
    async def handle_linkedin_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_linkedin(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_hobbies_drivers))
    async def handle_hobbies_drivers_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_hobbies_drivers(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_skills))
    async def handle_skills_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_skills(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_field_of_activity))
    async def handle_field_of_activity_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_field_of_activity(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_birthday))
    async def handle_birthday_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_birthday(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.waiting_for_photo))
    async def handle_photo_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_photo(message, state, db_pool)

    @dp.message(StateFilter(OnboardingStates.profile_confirmation))
    async def handle_profile_confirmation_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_profile_confirmation(message, state, db_pool, openai_client)

    @dp.message(StateFilter(OnboardingStates.partial_onboarding_confirmation))
    async def handle_partial_onboarding_confirmation_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        from scenes import handle_partial_onboarding_confirmation
        await handle_partial_onboarding_confirmation(message, state, db_pool)

    # Profile viewing and editing handlers
    @dp.message(StateFilter(ProfileStates.viewing_profile))
    async def handle_profile_view_state(message: Message, state: FSMContext):
        # Check if this is a thanks message first - process it regardless of state
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_profile_view_response(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_profile))
    async def handle_profile_edit_state(message: Message, state: FSMContext):
        # Check if this is a thanks message first - process it regardless of state
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_profile_edit_response(message, state, db_pool)

    # Edit mode handlers - these return to edit menu after updating field
    @dp.message(StateFilter(ProfileStates.editing_name))
    async def handle_name_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_name_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_location))
    async def handle_location_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_location_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_description))
    async def handle_description_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_description_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_linkedin))
    async def handle_linkedin_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_linkedin_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_hobbies_drivers))
    async def handle_hobbies_drivers_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_hobbies_drivers_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_skills))
    async def handle_skills_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_skills_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_field_of_activity))
    async def handle_field_of_activity_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_field_of_activity_edit_mode(message, state, db_pool)

    @dp.message(StateFilter(ProfileStates.editing_photo))
    async def handle_photo_edit_state(message: Message, state: FSMContext):
        if await _check_and_process_thanks(message, db_pool, bot):
            return
        await handle_photo_edit_mode(message, state, db_pool)

    # Birthday calendar callback handler
    @dp.callback_query(F.data.startswith("birthday_"))
    async def handle_birthday_callback_state(callback_query, state: FSMContext):
        await handle_birthday_callback(callback_query, state, db_pool)

    # Menu callback handlers
    @dp.callback_query(F.data.startswith("menu_"))
    async def handle_menu_callback(callback_query, state: FSMContext):
        """Handle menu button callbacks"""
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data == "menu_start":
            await callback_query.answer("Начинаем регистрацию...")
            await start_onboarding(callback_query.message, state, db_pool)
        elif data == "menu_edit_profile":
            await callback_query.answer("Редактирование профиля...")
            await handle_edit_profile(callback_query.message, state, db_pool)
        elif data == "menu_view_profile":
            await callback_query.answer("Просмотр профиля...")
            await handle_view_profile(callback_query.message, state, db_pool)
        elif data == "menu_report_issue":
            await callback_query.answer("Сообщение о проблеме...")
            await handle_report_issue(callback_query.message, state)
        elif data == "menu_suggest_feature":
            await callback_query.answer("Предложение функции...")
            await handle_suggest_feature(callback_query.message, state)
        elif data == "menu_my_matches":
            await callback_query.answer("Просмотр пар...")
            await handle_my_matches(callback_query.message)
        elif data == "menu_browse":
            await callback_query.answer("Просмотр пользователей...")
            await handle_people(callback_query.message)
        elif data == "menu_confirm_match":
            await callback_query.answer("Подтверждение пар...")
            await handle_confirm_match(callback_query.message, state)
        elif data == "menu_thanks":
            await callback_query.answer("Благодарности...")
            user_language = await get_user_language(db_pool, user_id)
            await handle_thanks_command(callback_query.message, db_pool, user_language, bot)
        elif data == "menu_stats":
            await callback_query.answer("Статистика...")
            user_language = await get_user_language(db_pool, user_id)
            await handle_stats_command(callback_query.message, db_pool, user_language, bot)
        elif data == "menu_top":
            await callback_query.answer("Топ пользователей...")
            user_language = await get_user_language(db_pool, user_id)
            await handle_top_command(callback_query.message, db_pool, user_language, bot)
        elif data == "menu_help":
            await callback_query.answer("Помощь...")
            await handle_help(callback_query.message)
        
        # Delete the menu message after selection
        try:
            await callback_query.message.delete()
        except Exception as e:
            print(f"Error deleting menu message: {e}")

    # Handle save/exit button responses
    # IMPORTANT: This handler must check for feedback_mode before clearing state
    # If user is in feedback mode (after /suggest_a_feature or /report_an_issue),
    # we should NOT clear state here - let echo_text handle it
    @dp.message(F.text.in_(["Сохранить", "Save", "Выход", "выход", "Exit", "exit"]))
    async def handle_save_exit_buttons(message: Message, state: FSMContext):
        """Handle save/exit button responses"""
        # Check if user is in feedback mode - if so, let echo_text handle it
        data = await state.get_data()
        is_feedback_mode = data and data.get("feedback_type") in ("issue", "feature")
        
        if is_feedback_mode:
            # User is providing feedback - let echo_text handle this message
            # Don't process exit button here, allow echo_text to process the feedback
            logger.debug(f"handle_save_exit_buttons: User in feedback mode, letting echo_text handle message: '{message.text}'")
            return
        
        current_state = await state.get_state()
        
        if message.text in ["Сохранить", "Save"]:
            # Get current data
            data = await state.get_data()
            
            # Save to database
            user_id = message.from_user.id
            await set_user_onboarding_data(db_pool, user_id, data, {})
            
            await message.answer("Профиль сохранен!" if message.text == "Сохранить" else "Profile saved!", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            
        elif message.text.lower() in ["выход", "exit"]:
            if current_state and "OnboardingStates" in str(current_state):
                await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
                await state.clear()
            else:
                await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())
                await state.clear()


    @dp.message(StateFilter("waiting_for_match_confirmation"))
    async def handle_match_confirmation(message: Message, state: FSMContext):
        """Handle match confirmation input"""
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        
        if not message.text:
            await message.answer(messages["COMMANDS"]["ENTER_VALID_MEETING_ID"])
            return
        
        try:
            meeting_id = int(message.text.strip())
        except ValueError:
            await message.answer(messages["COMMANDS"]["ENTER_VALID_MEETING_ID"])
            return
        
        # Get pending matches from state
        data = await state.get_data()
        pending_matches = data.get("pending_matches", [])
        
        # Find the matching meeting
        selected_meeting = None
        for match in pending_matches:
            if match['id'] == meeting_id:
                selected_meeting = match
                break
        
        if not selected_meeting:
            await message.answer(messages["COMMANDS"]["INVALID_MEETING_ID"])
            return
        
        # Update meeting status to 'matched'
        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE public.meetings
                SET status = 'matched', last_updated = NOW()
                WHERE id = $1
                """,
                meeting_id
            )
        
        # Get the other user's info
        user_id = message.from_user.id
        other_user_id = selected_meeting['user_2_id'] if selected_meeting['user_1_id'] == user_id else selected_meeting['user_1_id']
        other_user_name = selected_meeting['user2_name'] if selected_meeting['user_1_id'] == user_id else selected_meeting['user1_name']
        
        # Send confirmation to both users
        confirmation_text = f"✅ Match confirmed! You've been matched with {other_user_name}."
        await message.answer(confirmation_text)
        
        # Send notification to the other user
        try:
            other_user_text = f"✅ Your match with {message.from_user.first_name or 'Someone'} has been confirmed!"
            await send_message_throttled(other_user_id, other_user_text)
        except Exception as e:
            print(f"Error notifying other user {other_user_id}: {e}")
        
        # Clear state
        await state.clear()

    @dp.message(Command("scheduler_status"))
    async def handle_scheduler_status(message: Message):
        """Handle scheduler status command (admin only)"""
        from scheduler import get_scheduler_status
        from scenes import get_messages_dynamic
        messages = get_messages_dynamic(message.from_user.id)
        
        status = get_scheduler_status()
        status_text = f"📊 <b>{messages['COMMANDS']['SCHEDULER_STATUS']}</b>\n\n"
        
        if "error" in status:
            status_text += f"❌ {status['error']}"
        else:
            status_text += f"🔄 {messages['COMMANDS']['SCHEDULER_RUNNING']} {messages['COMMANDS']['SCHEDULER_YES'] if status['running'] else messages['COMMANDS']['SCHEDULER_NO']}\n\n"
            status_text += f"<b>{messages['COMMANDS']['SCHEDULER_JOBS']}</b>\n"
            
            for job_name, job_info in status['jobs'].items():
                status_text += f"• <b>{job_name}</b>\n"
                status_text += f"  {messages['COMMANDS']['LAST_RUN']} {job_info['last_run']}\n"
                status_text += f"  {messages['COMMANDS']['NEXT_RUN']} {job_info['next_run']}\n"
                status_text += f"  {messages['COMMANDS']['SCHEDULER_RUNNING']} {messages['COMMANDS']['SCHEDULER_YES'] if job_info['is_running'] else messages['COMMANDS']['SCHEDULER_NO']}\n"
                status_text += f"  {messages['COMMANDS']['INTERVAL']} {job_info['interval_hours']}h\n\n"
        
        await message.answer(status_text)

    @dp.message(Command("thanks"))
    async def handle_thanks_command_wrapper(message: Message, state: FSMContext):
        """Handle /thanks command"""
        if not _is_allowed_topic(message, "THANKS_TOPIC_ID"):
            return
        user_language = await get_user_language(db_pool, message.from_user.id)
        await handle_thanks_command(message, db_pool, user_language, bot)
    
    @dp.message(Command("check_birthdays"))
    async def handle_check_birthdays_command(message: Message, state: FSMContext):
        """Manually check and send birthday greetings (admin command)"""
        try:
            # Allow admin user to test birthday system regardless of topic
            user_id = message.from_user.id
            if user_id != 1541686636:  # Only allow admin user
                if not _is_allowed_topic(message, "BIRTHDAY_TOPIC_ID"):
                    return
            
            from birthday_greetings import check_and_send_birthday_greetings
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            await message.answer("🔄 Checking for birthdays today...")
            await check_and_send_birthday_greetings(bot, db_pool)
            await message.answer("✅ Birthday check completed!")
        except Exception as e:
            messages = get_messages_dynamic(message.from_user.id)
            await message.answer(f"❌ Birthday check error: {e}")
            logger.error(f"Error in check_birthdays command: {e}")

    @dp.message(Command("stats"))
    async def handle_stats_command_wrapper(message: Message, state: FSMContext):
        """Handle /stats command"""
        if not _is_allowed_topic(message, "THANKS_TOPIC_ID"):
            return
        user_language = await get_user_language(db_pool, message.from_user.id)
        await handle_stats_command(message, db_pool, user_language, bot)

    @dp.message(Command("top"))
    async def handle_top_command_wrapper(message: Message, state: FSMContext):
        """Handle /top [N] command"""
        if not _is_allowed_topic(message, "THANKS_TOPIC_ID"):
            return
        user_language = await get_user_language(db_pool, message.from_user.id)
        await handle_top_command(message, db_pool, user_language, bot)

    @dp.message(Command("generate_matches"))
    async def handle_generate_matches_command(message: Message, state: FSMContext):
        """Admin command to manually generate matches"""
        user_id = message.from_user.id
        
        # Get bot language from environment
        bot_language = os.getenv("BOT_LANGUAGE", "ru").lower()
        
        # Only allow specific admin user (anton_anisim0v) to use this command
        if user_id != 1541686636:  # anton_anisim0v's user ID
            error_msg = "Эта команда доступна только администраторам" if bot_language == "ru" else "This command is only available for administrators"
            await message.answer(error_msg)
            return
            
        try:
            # Import and use the match system
            from match_system import _match_system
            if not _match_system:
                error_msg = "Ошибка: Система матчинга не инициализирована" if bot_language == "ru" else "Error: Match system not initialized"
                await message.answer(error_msg)
                return
            
            # Get count of matchable users before generation
            from db import get_matchable_users
            matchable_users_before = await get_matchable_users(db_pool)
            
            # Generate matches
            pairs = await _match_system.generate_and_create_matches()
            
            # Build response message
            if bot_language == "ru":
                result_msg = "Генерация бизнес-партнерских связей\n\n"
                result_msg += f"Найдено подходящих пользователей: {len(matchable_users_before)}\n\n"
                
                if pairs:
                    # Notify users about matches
                    await _match_system.notify_matches(pairs)
                    result_msg += f"Создано новых пар: {len(pairs)}\n"
                    result_msg += f"Уведомлений отправлено: {len(pairs) * 2}\n\n"
                    result_msg += "Пользователи могут просмотреть свои бизнес-партнерские связи с помощью команды /my_matches"
                else:
                    result_msg += "Новые пары не созданы.\n\n"
                    result_msg += "Возможные причины:\n"
                    result_msg += "- Все возможные пары уже существуют\n"
                    result_msg += "- Недостаточно пользователей с достаточным порогом схожести\n"
                    result_msg += "- Пользователи не соответствуют критериям матчинга:\n"
                    result_msg += "  * finishedonboarding = true\n"
                    result_msg += "  * state = ACTIVE\n"
                    result_msg += "  * длина описания >= 10 символов\n"
                    result_msg += "  * matches_disabled = false или NULL"
            else:
                result_msg = "Business partner matching generation\n\n"
                result_msg += f"Found eligible users: {len(matchable_users_before)}\n\n"
                
                if pairs:
                    # Notify users about matches
                    await _match_system.notify_matches(pairs)
                    result_msg += f"Created new pairs: {len(pairs)}\n"
                    result_msg += f"Notifications sent: {len(pairs) * 2}\n\n"
                    result_msg += "Users can view their business partner connections with /my_matches command"
                else:
                    result_msg += "No new matches were generated.\n\n"
                    result_msg += "Possible reasons:\n"
                    result_msg += "- All possible pairs already exist\n"
                    result_msg += "- Not enough users with sufficient similarity threshold\n"
                    result_msg += "- Users do not meet matching criteria:\n"
                    result_msg += "  * finishedonboarding = true\n"
                    result_msg += "  * state = ACTIVE\n"
                    result_msg += "  * description length >= 10 characters\n"
                    result_msg += "  * matches_disabled = false or NULL"
            
            await message.answer(result_msg)
                    
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error during match generation: {error_details}")
            error_msg_ru = f"Ошибка при генерации матчей: {str(e)}"
            error_msg_en = f"Error during match generation: {str(e)}"
            await message.answer(error_msg_ru if bot_language == "ru" else error_msg_en)

    @dp.message(Command("enable_matches"))
    async def handle_enable_matches_command(message: Message, state: FSMContext):
        """Command for users to re-enable match recommendations"""
        user_id = message.from_user.id
        user_lang = await get_user_language(db_pool, user_id)
        
        try:
            # Check current status
            async with db_pool.acquire() as conn:
                user_row = await conn.fetchrow(
                    "SELECT matches_disabled FROM users WHERE user_id = $1",
                    user_id
                )
                
                if not user_row:
                    if user_lang == 'ru':
                        await message.answer("❌ Пользователь не найден.")
                    else:
                        await message.answer("❌ User not found.")
                    return
                
                if not user_row['matches_disabled']:
                    if user_lang == 'ru':
                        await message.answer("✅ Рекомендации уже включены.")
                    else:
                        await message.answer("✅ Recommendations are already enabled.")
                    return
                
                # Enable matches
                await enable_all_matches(db_pool, user_id)
                
                if user_lang == 'ru':
                    await message.answer("✅ Рекомендации включены. Вы снова будете получать новые рекомендации встреч.")
                else:
                    await message.answer("✅ Recommendations enabled. You will now receive new meeting recommendations.")
                    
        except Exception as e:
            logger.error(f"Error enabling matches: {e}", exc_info=True)
            if user_lang == 'ru':
                await message.answer("❌ Произошла ошибка при включении рекомендаций.")
            else:
                await message.answer("❌ An error occurred while enabling recommendations.")

    @dp.message(Command("admin_disable_matches"))
    async def handle_admin_disable_matches_command(message: Message, state: FSMContext):
        """Admin command to disable matches for a user"""
        user_id = message.from_user.id
        
        # Only allow specific admin user
        if user_id != 1541686636:
            await message.answer("❌ This command is only available for administrators")
            return
        
        try:
            # Parse command: /admin_disable_matches <user_id>
            command_parts = message.text.split()
            if len(command_parts) < 2:
                await message.answer("❌ Usage: /admin_disable_matches <user_id>\nExample: /admin_disable_matches 123456789")
                return
            
            target_user_id = int(command_parts[1])
            
            # Check if user exists
            user_info = await get_user_info(db_pool, target_user_id)
            if not user_info:
                await message.answer(f"❌ User {target_user_id} not found.")
                return
            
            # Disable matches
            await disable_all_matches(db_pool, target_user_id)
            
            await message.answer(f"✅ Matches disabled for user {target_user_id} ({user_info.get('intro_name', 'Unknown')})")
            
        except ValueError:
            await message.answer("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in admin_disable_matches: {e}", exc_info=True)
            await message.answer(f"❌ Error: {str(e)}")

    @dp.message(Command("admin_enable_matches"))
    async def handle_admin_enable_matches_command(message: Message, state: FSMContext):
        """Admin command to enable matches for a user"""
        user_id = message.from_user.id
        
        # Only allow specific admin user
        if user_id != 1541686636:
            await message.answer("❌ This command is only available for administrators")
            return
        
        try:
            # Parse command: /admin_enable_matches <user_id>
            command_parts = message.text.split()
            if len(command_parts) < 2:
                await message.answer("❌ Usage: /admin_enable_matches <user_id>\nExample: /admin_enable_matches 123456789")
                return
            
            target_user_id = int(command_parts[1])
            
            # Check if user exists
            user_info = await get_user_info(db_pool, target_user_id)
            if not user_info:
                await message.answer(f"❌ User {target_user_id} not found.")
                return
            
            # Enable matches
            await enable_all_matches(db_pool, target_user_id)
            
            await message.answer(f"✅ Matches enabled for user {target_user_id} ({user_info.get('intro_name', 'Unknown')})")
            
        except ValueError:
            await message.answer("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in admin_enable_matches: {e}", exc_info=True)
            await message.answer(f"❌ Error: {str(e)}")

    @dp.message(Command("test_birthday"))
    async def handle_test_birthday_command(message: Message, state: FSMContext):
        """Admin command to test birthday notification system"""
        user_id = message.from_user.id
        
        # Only allow specific admin user (anton_anisim0v) to use this command
        if user_id != 1541686636:  # anton_anisim0v's user ID
            await message.answer("❌ This command is only available for administrators")
            return
            
        try:
            from datetime import date
            await message.answer("🔄 Setting your birthday to today for testing...")
            
            # Set birthday to today
            today = date.today()
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET intro_birthday = $1 WHERE user_id = $2",
                    today, user_id
                )
            
            await message.answer(f"✅ Birthday set to today: {today}")
            await message.answer("🔄 Now triggering birthday notification to birthday topic...")
            
            # Check if birthday topic is configured
            birthday_topic_id = os.getenv("BIRTHDAY_TOPIC_ID")
            group_chat_id = os.getenv("TELEGRAM_GROUP_ID")
            
            if not birthday_topic_id or not group_chat_id:
                await message.answer("❌ Birthday topic not configured. Please set BIRTHDAY_TOPIC_ID and TELEGRAM_GROUP_ID in environment variables.")
                return
            
            await message.answer(f"📋 Birthday topic ID: {birthday_topic_id}")
            await message.answer(f"📋 Group chat ID: {group_chat_id}")
            
            # Trigger birthday check
            from birthday_greetings import check_and_send_birthday_greetings
            await check_and_send_birthday_greetings(bot, db_pool)
            await message.answer("✅ Birthday notification test completed! Check the birthday topic in the group.")
                    
        except Exception as e:
            await message.answer(f"❌ Error during birthday test: {str(e)}")

    @dp.message(Command("say"))
    async def handle_say_command(message: Message, state: FSMContext):
        """Handle /say command to get ChatGPT response"""
        # Skip processing if user is in onboarding state
        current_state = await state.get_state()
        if current_state and current_state.startswith("OnboardingStates"):
            await message.answer("Пожалуйста, завершите регистрацию перед использованием этой команды.")
            return
        
        # Get the text after /say command
        command_text = message.text or ""
        if command_text.startswith("/say "):
            user_question = command_text[5:].strip()  # Remove "/say " prefix
        else:
            user_question = ""
        
        if not user_question:
            await message.answer("Использование: /say <ваш вопрос>\nНапример: /say Как дела?")
            return
        
        if openai_client:
            try:
                completion = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_question},
                    ],
                    max_tokens=200,
                )
                reply = completion.choices[0].message.content or "Извините, не удалось получить ответ."
            except Exception as e:
                logger.error(f"Error with ChatGPT: {e}")
                reply = "Извините, произошла ошибка при обращении к ChatGPT."
        else:
            reply = "ChatGPT недоступен. Проверьте настройки OPENAI_API_KEY."

        await message.answer(reply)

    @dp.message(F.text)
    async def echo_text(message: Message, state: FSMContext):
        # Skip processing for commands that should be handled by specific handlers
        if message.text and message.text.startswith("/"):
            # Let command handlers process this
            return
        
        # Handle Exit button - but only if NOT in feedback mode
        # If user is providing feedback, "Выход" should be treated as feedback text, not exit command
        data_before_exit_check = await state.get_data()
        is_feedback_mode = data_before_exit_check and data_before_exit_check.get("feedback_type") in ("issue", "feature")
        
        if message.text and message.text.lower() in ["выход", "exit"] and not is_feedback_mode:
            # User wants to exit (and not in feedback mode)
            await state.clear()
            await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())
            return
        
        # Skip processing if user is in onboarding state - let state handlers process this
        current_state = await state.get_state()
        if current_state and current_state.startswith("OnboardingStates"):
            # Let onboarding state handlers process this message
            return
            
        # Example of saving minimal message record according to plan
        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                insert into bot_messages(user_id, chat_id, text, created_at)
                values($1, $2, $3, now())
                """,
                message.from_user.id if message.from_user else None,
                message.chat.id,
                message.text,
            )
        
        
        # Check if this is a followup response
        if message.text and ("yes" in message.text.lower() or "no" in message.text.lower() or "✅" in message.text or "❌" in message.text):
            try:
                await handle_followup_response(message.from_user.id, message.text)
                return
            except Exception as e:
                print(f"Error handling followup response: {e}")
        
        # Check for thanks messages BEFORE feedback processing
        # Only check if message has mentions (to avoid duplicate processing)
        has_mention = False
        if message.text and ("@" in message.text or "t.me/" in message.text.lower()):
            has_mention = True
        elif message.entities:
            for entity in message.entities:
                if entity.type in ('text_mention', 'mention'):
                    has_mention = True
                    break
        
        if has_mention:
            # Check if this is a thanks message
            thanks_processed = await _check_and_process_thanks(message, db_pool, bot)
            if thanks_processed:
                logger.info(f"echo_text: thanks processed for message '{message.text}'")
                return
        
        # Feedback capture when in feedback mode
        data = await state.get_data()
        feedback_type_in_state = data.get('feedback_type') if data else None
        logger.info(f"echo_text handler: user_id={message.from_user.id}, text_length={len(message.text) if message.text else 0}, state_data={data}, feedback_type={feedback_type_in_state}, current_state={current_state}")
        
        if data and data.get("feedback_type") in ("issue", "feature"):
            feedback_type = data["feedback_type"]
            telegram_user_id = message.from_user.id
            feedback_text = message.text
            logger.info(f"echo_text: Processing feedback - type={feedback_type}, user_id={telegram_user_id}, text_preview={feedback_text[:50] if feedback_text else 'None'}...")
            
            # Validate feedback text
            if len(feedback_text.strip()) < 10:
                await message.answer(
                    "❌ Пожалуйста, предоставьте больше деталей. Ваш отзыв должен содержать минимум 10 символов."
                )
                return
            
            # Ensure user exists in database with correct user_id (handle migration if needed)
            # Check if user exists with real user_id, if not, try to find and migrate from temporary ID
            async with db_pool.acquire() as conn:
                existing_user = await conn.fetchrow(
                    "SELECT user_id FROM users WHERE user_id = $1",
                    telegram_user_id
                )
                
                # If user doesn't exist with real ID, try to migrate from temporary ID
                if not existing_user:
                    username = message.from_user.username
                    first_name = message.from_user.first_name
                    last_name = message.from_user.last_name
                    
                    temp_user = None
                    # Try by username first
                    if username:
                        temp_user = await conn.fetchrow(
                            "SELECT user_id, finishedonboarding, state FROM users WHERE user_id < 0 AND LOWER(user_telegram_link) = LOWER($1)",
                            username
                        )
                    # Try by name if username didn't match
                    if not temp_user and first_name:
                        telegram_full_name = f"{first_name} {last_name}".strip() if last_name else first_name
                        temp_user = await conn.fetchrow(
                            "SELECT user_id, finishedonboarding, state FROM users WHERE user_id < 0 AND (intro_name ILIKE $1 OR $2 ILIKE '%' || TRIM(intro_name) || '%')",
                            f"%{telegram_full_name}%", telegram_full_name
                        )
                    
                    if temp_user:
                        logger.info(f"Migrating user from {temp_user['user_id']} to {telegram_user_id} before saving feedback")
                        finishedonboarding_value = temp_user.get('finishedonboarding', True)
                        state_value = temp_user.get('state', 'ACTIVE')
                        await conn.execute(
                            "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                            telegram_user_id, temp_user['user_id'], finishedonboarding_value, state_value
                        )
                        # Also migrate existing feedbacks
                        await conn.execute(
                            "UPDATE feedbacks SET user_id = $1 WHERE user_id = $2",
                            telegram_user_id, temp_user['user_id']
                        )
                        logger.info(f"✓ Migrated user {temp_user['user_id']} -> {telegram_user_id} before feedback save")
            
            # Save feedback to database with correct user_id
            try:
                logger.info(f"Saving feedback: user_id={telegram_user_id}, type={feedback_type}, text_length={len(feedback_text)}")
                await insert_feedback(db_pool, telegram_user_id, feedback_type, feedback_text)
                logger.info(f"✓ Successfully saved feedback for user {telegram_user_id}, type: {feedback_type}")
            except Exception as e:
                logger.error(f"Error saving feedback to database: {e}", exc_info=True)
                await message.answer("❌ Произошла ошибка при сохранении вашего отзыва. Пожалуйста, попробуйте позже.")
                return
            
            # Send notification to admin
            try:
                await notify_feedback(telegram_user_id, feedback_type, feedback_text)
            except Exception as e:
                logger.error(f"Error sending feedback notification: {e}")
            
            # Send localized confirmation message
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            
            if feedback_type == "issue":
                confirmation = f"✅ {messages['COMMANDS']['FEEDBACK_THANK_ISSUE']}"
            else:  # feature
                confirmation = f"✅ {messages['COMMANDS']['FEEDBACK_THANK_IDEA']}"
            
            await message.answer(confirmation)
            await state.clear()
            return
        # No automatic ChatGPT responses - only /say command triggers ChatGPT

    # My Matches callback handlers
    @dp.callback_query(F.data == "my_matches_next")
    async def handle_my_matches_next(callback_query, state: FSMContext):
        """Handle Next button in my matches"""
        data = await state.get_data()
        matches = data.get("matches", [])
        current_index = data.get("current_index", 0)
        
        if current_index < len(matches) - 1:
            new_index = current_index + 1
            await state.update_data(current_index=new_index)
            await show_match_profile(callback_query.message, matches[new_index], new_index, len(matches))
        
        await callback_query.answer()
    
    @dp.callback_query(F.data == "my_matches_browse")
    async def handle_my_matches_browse(callback_query, state: FSMContext):
        """Handle See all users button - switch to browse mode"""
        await state.clear()
        await state.set_state(BrowseStates.browsing_users)
        
        # Get all users for browsing (same logic as /browse command)
        async with db_pool.acquire() as connection:
            rows = await connection.fetch(
                """
                select user_id, coalesce(intro_name, 'No name') as intro_name,
                       coalesce(intro_location, 'No location') as intro_location,
                       coalesce(intro_description, 'No description') as intro_description,
                       coalesce(intro_linkedin, 'No LinkedIn') as intro_linkedin,
                       intro_image, user_telegram_link, intro_hobbies_drivers, intro_skills, intro_birthday
                from public.users
                where finishedonboarding = true
                and user_id != $1
                order by intro_name
                """,
                callback_query.from_user.id
            )
        
        if not rows:
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            await callback_query.message.edit_text(messages["COMMANDS"]["BROWSE_NO_USERS"])
            await state.clear()
            return
        
        users = [dict(row) for row in rows]
        await state.update_data(browse_users=users, browse_index=0)
        await show_browse_profile(callback_query.message, users[0], 0, len(users), state)
        await callback_query.answer()
    
    @dp.callback_query(F.data == "my_matches_exit")
    async def handle_my_matches_exit(callback_query, state: FSMContext):
        """Handle Exit button in my matches"""
        await state.clear()
        await callback_query.message.edit_text("Просмотр контактов завершен.")
        await callback_query.answer()
    
    # Match action callback handlers
    @dp.callback_query(F.data.startswith("match_met_"))
    async def handle_match_met(callback_query, state: FSMContext):
        """Handle 'Meeting completed' button"""
        print(f"[DEBUG] handle_match_met called: callback_data={callback_query.data}, user_id={callback_query.from_user.id}")
        try:
            meeting_id = callback_query.data.replace("match_met_", "")
            user_id = callback_query.from_user.id
            
            logger.info(f"handle_match_met called with callback_data: {callback_query.data}, user_id: {user_id}, meeting_id: {meeting_id}")
            
            # Get user language for response
            user_lang = await get_user_language(db_pool, user_id)
            
            # Update meeting status to indicate they met
            meeting = await get_meeting_by_id(db_pool, meeting_id)
            logger.info(f"Meeting lookup result: {meeting is not None}")
            
            if meeting:
                await update_meeting_status(db_pool, meeting_id, "met")
                logger.info(f"Meeting {meeting_id} status updated to 'met'")
                
                # Update call_successful to True (if column exists)
                try:
                    async with db_pool.acquire() as connection:
                        # Check if call_successful column exists
                        column_check = await connection.fetchrow(
                            """
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'meetings' 
                            AND table_schema = 'public' 
                            AND column_name = 'call_successful'
                            """
                        )
                        if column_check:
                            await connection.execute(
                                """
                                UPDATE public.meetings
                                SET call_successful = true, last_updated = NOW()
                                WHERE id = $1
                                """,
                                int(meeting_id)
                            )
                            logger.info(f"Meeting {meeting_id} call_successful set to true")
                        else:
                            logger.warning(f"call_successful column does not exist, skipping")
                except Exception as update_error:
                    logger.warning(f"Could not update call_successful: {update_error}")
                
                if user_lang == 'ru':
                    response_text = "Спасибо! Следующая встреча с этим контактом будет предложена через 6 месяцев."
                    status_marker = "\n\n— <b>Встреча отмечена как состоявшаяся</b>\nСледующая встреча с этим контактом будет предложена через 6 месяцев."
                else:
                    response_text = "Thank you! Next meeting with this contact will be suggested in 6 months."
                    status_marker = "\n\n— <b>Meeting marked as completed</b>\nNext meeting with this contact will be suggested in 6 months."
                
                await callback_query.answer(response_text, show_alert=False)
                
                # Update message text to show status and remove keyboard
                try:
                    current_text = callback_query.message.text or callback_query.message.caption or ""
                    updated_text = current_text + status_marker
                    await callback_query.message.edit_text(updated_text, parse_mode="HTML", reply_markup=None)
                except Exception as edit_error:
                    logger.warning(f"Could not update message text, trying to remove keyboard only: {edit_error}")
                    try:
                        await callback_query.message.edit_reply_markup(reply_markup=None)
                    except Exception as edit_error2:
                        logger.warning(f"Could not remove keyboard: {edit_error2}")
                
                logger.info(f"Successfully handled match_met for user {user_id}")
            else:
                logger.error(f"Meeting {meeting_id} not found for user {user_id}")
                if user_lang == 'ru':
                    error_text = "❌ Встреча не найдена."
                else:
                    error_text = "❌ Meeting not found."
                await callback_query.answer(error_text, show_alert=True)
        except Exception as e:
            logger.error(f"Error handling match_met: {e}", exc_info=True)
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            if user_lang == 'ru':
                error_text = "❌ Произошла ошибка."
            else:
                error_text = "❌ An error occurred."
            await callback_query.answer(error_text, show_alert=True)
    
    @dp.callback_query(F.data.startswith("match_block_"))
    async def handle_match_block(callback_query, state: FSMContext):
        """Handle 'Exclude contact' button"""
        print(f"[DEBUG] handle_match_block called: callback_data={callback_query.data}, user_id={callback_query.from_user.id}")
        try:
            logger.info(f"handle_match_block called with callback_data: {callback_query.data}, user_id: {callback_query.from_user.id}")
            
            # Parse callback data: match_block_{meeting_id}_{blocked_user_id}
            parts = callback_query.data.replace("match_block_", "").split("_")
            logger.info(f"Parsed parts: {parts}")
            
            if len(parts) < 2:
                logger.error(f"Invalid callback data format: {callback_query.data}, parts: {parts}")
                user_lang = await get_user_language(db_pool, callback_query.from_user.id)
                if user_lang == 'ru':
                    error_text = "❌ Неверный формат данных."
                else:
                    error_text = "❌ Invalid data format."
                await callback_query.answer(error_text, show_alert=True)
                return
            
            meeting_id = parts[0]
            blocked_user_id = int(parts[1])
            user_id = callback_query.from_user.id
            
            logger.info(f"Blocking: user_id={user_id}, blocked_user_id={blocked_user_id}, meeting_id={meeting_id}")
            
            # Get user language for response
            user_lang = await get_user_language(db_pool, user_id)
            
            # Block the user
            await block_user(db_pool, user_id, blocked_user_id)
            logger.info(f"User {blocked_user_id} blocked by user {user_id}")
            
            # Update meeting status
            await update_meeting_status(db_pool, meeting_id, "blocked")
            logger.info(f"Meeting {meeting_id} status updated to 'blocked'")
            
            if user_lang == 'ru':
                response_text = "Контакт исключен из рекомендаций."
                status_marker = "\n\n— <b>Контакт исключен из рекомендаций</b>"
            else:
                response_text = "Contact excluded from recommendations."
                status_marker = "\n\n— <b>Contact excluded from recommendations</b>"
            
            await callback_query.answer(response_text, show_alert=False)
            
            # Update message text to show status and remove keyboard
            try:
                current_text = callback_query.message.text or callback_query.message.caption or ""
                updated_text = current_text + status_marker
                await callback_query.message.edit_text(updated_text, parse_mode="HTML", reply_markup=None)
            except Exception as edit_error:
                logger.warning(f"Could not update message text, trying to remove keyboard only: {edit_error}")
                try:
                    await callback_query.message.edit_reply_markup(reply_markup=None)
                except Exception as edit_error2:
                    logger.warning(f"Could not remove keyboard: {edit_error2}")
            
            logger.info(f"Successfully handled match_block for user {user_id}")
        except Exception as e:
            logger.error(f"Error handling match_block: {e}", exc_info=True)
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            if user_lang == 'ru':
                error_text = "❌ Произошла ошибка."
            else:
                error_text = "❌ An error occurred."
            await callback_query.answer(error_text, show_alert=True)
    
    @dp.callback_query(F.data.startswith("match_disable_"))
    async def handle_match_disable(callback_query, state: FSMContext):
        """Handle 'Disable recommendations' button"""
        print(f"[DEBUG] handle_match_disable called: callback_data={callback_query.data}, user_id={callback_query.from_user.id}")
        try:
            meeting_id = callback_query.data.replace("match_disable_", "")
            user_id = callback_query.from_user.id
            
            logger.info(f"handle_match_disable called with callback_data: {callback_query.data}, user_id: {user_id}, meeting_id: {meeting_id}")
            
            # Get user language for response
            user_lang = await get_user_language(db_pool, user_id)
            
            # Disable all matches for this user
            await disable_all_matches(db_pool, user_id)
            logger.info(f"Matches disabled for user {user_id}")
            
            # Update meeting status
            await update_meeting_status(db_pool, meeting_id, "matches_disabled")
            logger.info(f"Meeting {meeting_id} status updated to 'matches_disabled'")
            
            if user_lang == 'ru':
                response_text = "Рекомендации отключены. Вы больше не будете получать новые рекомендации встреч."
            else:
                response_text = "Recommendations disabled. You will no longer receive new meeting recommendations."
            
            # Use show_alert=True for more visible notification
            await callback_query.answer(response_text, show_alert=True)
            
            # Update keyboard: replace "Disable recommendations" button with "Enable recommendations"
            # Keep other buttons (View Profile, Meeting completed, Exclude contact)
            try:
                current_keyboard = callback_query.message.reply_markup
                logger.info(f"Current keyboard: {current_keyboard}")
                if current_keyboard and current_keyboard.inline_keyboard:
                    # Get button texts based on language
                    if user_lang == 'ru':
                        button_enable = "🔄 Включить рекомендации"
                    else:
                        button_enable = "🔄 Enable recommendations"
                    
                    # Create new keyboard with "Enable" button instead of "Disable"
                    new_keyboard_buttons = []
                    button_replaced = False
                    for row in current_keyboard.inline_keyboard:
                        new_row = []
                        for button in row:
                            # Replace "Disable" button with "Enable" button
                            if button.callback_data and button.callback_data.startswith("match_disable_"):
                                from aiogram.types import InlineKeyboardButton
                                logger.info(f"Replacing button: {button.callback_data} -> match_enable_{meeting_id}")
                                new_row.append(InlineKeyboardButton(
                                    text=button_enable,
                                    callback_data=f"match_enable_{meeting_id}"
                                ))
                                button_replaced = True
                            else:
                                new_row.append(button)
                        if new_row:  # Only add row if it has buttons
                            new_keyboard_buttons.append(new_row)
                    
                    if not button_replaced:
                        logger.warning(f"Button 'match_disable_' not found in keyboard, adding enable button")
                        # If button not found, add enable button as new row
                        new_keyboard_buttons.append([
                            InlineKeyboardButton(
                                text=button_enable,
                                callback_data=f"match_enable_{meeting_id}"
                            )
                        ])
                    
                    # Create new keyboard
                    from aiogram.types import InlineKeyboardMarkup
                    new_keyboard = InlineKeyboardMarkup(inline_keyboard=new_keyboard_buttons) if new_keyboard_buttons else None
                    logger.info(f"New keyboard created with {len(new_keyboard_buttons)} rows")
                    
                    # Update message with new keyboard
                    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)
                    logger.info(f"Keyboard updated successfully")
                else:
                    logger.warning(f"No keyboard found in message, cannot update")
            except Exception as edit_error:
                logger.error(f"Could not update keyboard: {edit_error}", exc_info=True)
                # Don't remove keyboard on error - just log it
            
            logger.info(f"Successfully handled match_disable for user {user_id}")
            print(f"[SUCCESS] match_disable completed for user {user_id}, matches_disabled set to True")
        except Exception as e:
            logger.error(f"Error handling match_disable: {e}", exc_info=True)
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            if user_lang == 'ru':
                error_text = "❌ Произошла ошибка."
            else:
                error_text = "❌ An error occurred."
            await callback_query.answer(error_text, show_alert=True)

    @dp.callback_query(F.data.startswith("match_enable_"))
    async def handle_match_enable(callback_query, state: FSMContext):
        """Handle 'Enable recommendations' button"""
        print(f"[DEBUG] handle_match_enable called: callback_data={callback_query.data}, user_id={callback_query.from_user.id}")
        try:
            meeting_id = callback_query.data.replace("match_enable_", "")
            user_id = callback_query.from_user.id
            
            logger.info(f"handle_match_enable called with callback_data: {callback_query.data}, user_id: {user_id}, meeting_id: {meeting_id}")
            
            # Get user language for response
            user_lang = await get_user_language(db_pool, user_id)
            
            # Enable all matches for this user
            await enable_all_matches(db_pool, user_id)
            logger.info(f"Matches enabled for user {user_id}")
            
            # Update meeting status
            await update_meeting_status(db_pool, meeting_id, "matches_enabled")
            logger.info(f"Meeting {meeting_id} status updated to 'matches_enabled'")
            
            if user_lang == 'ru':
                response_text = "Рекомендации включены. Вы снова будете получать новые рекомендации встреч."
            else:
                response_text = "Recommendations enabled. You will now receive new meeting recommendations."
            
            # Use show_alert=True for more visible notification
            await callback_query.answer(response_text, show_alert=True)
            
            # Update keyboard: replace "Enable recommendations" button with "Disable recommendations"
            # Keep other buttons (View Profile, Meeting completed, Exclude contact)
            try:
                current_keyboard = callback_query.message.reply_markup
                if current_keyboard and current_keyboard.inline_keyboard:
                    # Get button texts based on language
                    if user_lang == 'ru':
                        button_disable = "⛔ Отключить рекомендации"
                    else:
                        button_disable = "⛔ Disable recommendations"
                    
                    # Create new keyboard with "Disable" button instead of "Enable"
                    new_keyboard_buttons = []
                    for row in current_keyboard.inline_keyboard:
                        new_row = []
                        for button in row:
                            # Replace "Enable" button with "Disable" button
                            if button.callback_data and button.callback_data.startswith("match_enable_"):
                                from aiogram.types import InlineKeyboardButton
                                new_row.append(InlineKeyboardButton(
                                    text=button_disable,
                                    callback_data=f"match_disable_{meeting_id}"
                                ))
                            else:
                                new_row.append(button)
                        if new_row:  # Only add row if it has buttons
                            new_keyboard_buttons.append(new_row)
                    
                    # Create new keyboard
                    from aiogram.types import InlineKeyboardMarkup
                    new_keyboard = InlineKeyboardMarkup(inline_keyboard=new_keyboard_buttons) if new_keyboard_buttons else None
                    
                    # Update message with new keyboard
                    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)
                else:
                    # If no keyboard, just remove it
                    await callback_query.message.edit_reply_markup(reply_markup=None)
            except Exception as edit_error:
                logger.warning(f"Could not update keyboard: {edit_error}")
                # Fallback: try to remove entire keyboard
                try:
                    await callback_query.message.edit_reply_markup(reply_markup=None)
                except Exception as edit_error2:
                    logger.warning(f"Could not remove keyboard: {edit_error2}")
            
            logger.info(f"Successfully handled match_enable for user {user_id}")
            print(f"[SUCCESS] match_enable completed for user {user_id}, matches_disabled set to False")
        except Exception as e:
            logger.error(f"Error handling match_enable: {e}", exc_info=True)
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            if user_lang == 'ru':
                error_text = "❌ Произошла ошибка."
            else:
                error_text = "❌ An error occurred."
            await callback_query.answer(error_text, show_alert=True)
    
    # Browse callback handlers
    @dp.callback_query(F.data == "browse_next")
    async def handle_browse_next(callback_query, state: FSMContext):
        """Handle Next button in browse"""
        data = await state.get_data()
        users = data.get("browse_users", [])
        current_index = data.get("browse_index", 0)
        
        if current_index < len(users) - 1:
            new_index = current_index + 1
            await state.update_data(browse_index=new_index)
            await show_browse_profile(callback_query.message, users[new_index], new_index, len(users), state)
        
        await callback_query.answer()
    
    @dp.callback_query(F.data == "browse_previous")
    async def handle_browse_previous(callback_query, state: FSMContext):
        """Handle Previous button in browse"""
        data = await state.get_data()
        users = data.get("browse_users", [])
        current_index = data.get("browse_index", 0)
        
        if current_index > 0:
            new_index = current_index - 1
            await state.update_data(browse_index=new_index)
            await show_browse_profile(callback_query.message, users[new_index], new_index, len(users), state)
        
        await callback_query.answer()
    
    @dp.callback_query(F.data == "browse_exit")
    async def handle_browse_exit(callback_query, state: FSMContext):
        """Handle Exit button in browse"""
        # Clean up photo and text messages in parallel for faster response
        data = await state.get_data()
        photo_message_id = data.get("browse_photo_message_id")
        text_message_id = data.get("browse_text_message_id")
        
        import asyncio
        
        async def delete_photo_message():
            if photo_message_id:
                try:
                    await callback_query.bot.delete_message(callback_query.message.chat.id, photo_message_id)
                    print(f"DEBUG: Deleted photo message ID: {photo_message_id} on browse exit")
                except Exception as delete_error:
                    print(f"DEBUG: Could not delete photo on browse exit: {delete_error}")
        
        async def delete_text_message():
            if text_message_id:
                try:
                    await callback_query.bot.delete_message(callback_query.message.chat.id, text_message_id)
                    print(f"DEBUG: Deleted text message ID: {text_message_id} on browse exit")
                except Exception as delete_error:
                    print(f"DEBUG: Could not delete text on browse exit: {delete_error}")
        
        async def edit_current_message():
            try:
                await callback_query.message.edit_text("Просмотр пользователей завершен.")
            except Exception as edit_error:
                print(f"DEBUG: Could not edit current message on browse exit: {edit_error}")
        
        # Execute all operations in parallel
        await asyncio.gather(
            delete_photo_message(),
            delete_text_message(),
            edit_current_message(),
            return_exceptions=True
        )
        
        await state.clear()
        await callback_query.answer()

    # Callback handler for viewing profile from match notification
    @dp.callback_query(F.data.startswith("view_profile_"))
    async def handle_view_profile_callback(callback_query, state: FSMContext):
        """Handle clicks on 'View Profile' button from match notifications"""
        try:
            user_id = int(callback_query.data.split("_")[-1])
            
            # Get full user information
            user_info = await get_user_info(db_pool, user_id)
            
            if not user_info:
                user_lang = await get_user_language(db_pool, callback_query.from_user.id)
                error_text = "Пользователь не найден" if user_lang == 'ru' else "User not found"
                await callback_query.answer(error_text)
                return
            
            # Show profile using the same logic as browse_user
            photo_message_id = None
            
            # Send photo first if available
            if user_info.get("intro_image"):
                try:
                    import base64
                    import aiohttp
                    from aiogram.types import BufferedInputFile
                    
                    image_data = user_info["intro_image"]
                    
                    # Handle different image formats
                    if image_data.startswith('data:image/'):
                        base64_data = image_data.split(',')[1]
                        photo_data = base64.b64decode(base64_data)
                    elif image_data.startswith(('http://', 'https://')):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_data) as response:
                                if response.status == 200:
                                    photo_data = await response.read()
                                else:
                                    print(f"DEBUG: Failed to download image from URL: {response.status}")
                                    photo_data = None
                    else:
                        photo_data = base64.b64decode(image_data)
                    
                    if photo_data:
                        input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                        photo_message = await callback_query.message.answer_photo(input_file)
                        photo_message_id = photo_message.message_id
                except Exception as photo_error:
                    print(f"DEBUG: Error sending photo: {photo_error}")
            
            # Build and send profile text
            from scenes import build_profile_text
            profile_text = build_profile_text(user_info, user_id=callback_query.from_user.id, is_own_profile=False)
            
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            if user_lang == 'ru':
                await callback_query.answer("Профиль загружается...")
            else:
                await callback_query.answer("Loading profile...")
            
            await callback_query.message.answer(profile_text, parse_mode="HTML")
            
        except ValueError:
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            error_text = "Неверный ID пользователя" if user_lang == 'ru' else "Invalid user ID"
            await callback_query.answer(error_text)
        except Exception as e:
            logger.error(f"Error in handle_view_profile_callback: {e}", exc_info=True)
            user_lang = await get_user_language(db_pool, callback_query.from_user.id)
            error_text = "Произошла ошибка" if user_lang == 'ru' else "An error occurred"
            await callback_query.answer(error_text)

    # Callback handler for user detail buttons
    @dp.callback_query(F.data.startswith("browse_user_"))
    async def handle_browse_user_callback(callback_query, state: FSMContext):
        """Handle clicks on user buttons from /browse - shows full profile like /view_profile"""
        try:
            user_id = int(callback_query.data.split("_")[-1])
            
            # Get full user information like in /browse command
            async with db_pool.acquire() as connection:
                user_info = await get_user_info(db_pool, user_id)
            
            if not user_info:
                await callback_query.answer("Пользователь не найден")
                return
            
            photo_message_id = None
            
            # Send photo first if available (same as /browse command)
            if user_info.get("intro_image"):
                try:
                    import base64
                    import aiohttp
                    from aiogram.types import BufferedInputFile
                    
                    image_data = user_info["intro_image"]
                    
                    # Handle different image formats
                    if image_data.startswith('data:image/'):
                        # Data URL format - extract base64 part
                        base64_data = image_data.split(',')[1]
                        photo_data = base64.b64decode(base64_data)
                    elif image_data.startswith(('http://', 'https://')):
                        # URL format - download and convert to base64
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_data) as response:
                                if response.status == 200:
                                    photo_data = await response.read()
                                else:
                                    print(f"DEBUG: Failed to download image from URL: {response.status}")
                                    return
                    else:
                        # Assume it's raw base64 data
                        photo_data = base64.b64decode(image_data)
                    
                    # Create BufferedInputFile for aiogram
                    input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                    photo_message = await callback_query.message.answer_photo(input_file)
                    photo_message_id = photo_message.message_id
                except Exception as photo_error:
                    print(f"DEBUG: Error sending photo: {photo_error}")
                    # Continue without photo if there's an error
                    photo_message_id = None
            
            # Send profile details using the same format as /browse
            from scenes import build_profile_text
            profile_text = build_profile_text(user_info, callback_query.from_user.id, is_own_profile=False)
            
            # Add close button with photo message ID stored in callback data
            close_callback_data = f"close_profile_with_photo_{photo_message_id}" if photo_message_id else "close_user_detail"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Закрыть", callback_data=close_callback_data)]
            ])
            
            await callback_query.message.answer(profile_text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer()
            
        except Exception as e:
            await callback_query.answer("Ошибка при получении профиля пользователя")
            logger.error(f"Error in handle_browse_user_callback: {e}")

    @dp.callback_query(F.data == "close_user_detail")
    async def handle_close_user_detail(callback_query, state: FSMContext):
        """Handle close button for user details - closes profile only (no photo)"""
        try:
            # Delete the current message (profile details)
            await callback_query.message.delete()
            await callback_query.answer("Профиль закрыт")
            
        except Exception as e:
            logger.error(f"Error closing user detail: {e}")
            await callback_query.answer("Профиль закрыт")

    @dp.callback_query(F.data.startswith("close_profile_with_photo_"))
    async def handle_close_profile_with_photo(callback_query, state: FSMContext):
        """Handle close button for user details with photo - closes both profile text and photo"""
        try:
            # Extract photo message ID from callback data
            photo_message_id = int(callback_query.data.split("_")[-1])
            
            chat_id = callback_query.message.chat.id
            current_message_id = callback_query.message.message_id
            
            # Delete both messages in parallel for faster response
            import asyncio
            
            async def delete_profile_message():
                try:
                    await callback_query.message.delete()
                except Exception as e:
                    logger.warning(f"Could not delete profile message: {e}")
            
            async def delete_photo_message():
                try:
                    await callback_query.bot.delete_message(chat_id, photo_message_id)
                except Exception as e:
                    logger.warning(f"Could not delete profile photo (ID: {photo_message_id}): {e}")
            
            # Execute both deletions in parallel
            await asyncio.gather(
                delete_profile_message(),
                delete_photo_message(),
                return_exceptions=True
            )
            
            await callback_query.answer("Профиль закрыт")
            
        except Exception as e:
            logger.error(f"Error closing user detail with photo: {e}")
            await callback_query.answer("Профиль закрыт")

    # Callback handlers for list actions
    @dp.callback_query(F.data == "refresh_user_list")
    async def handle_refresh_user_list(callback_query, state: FSMContext):
        """Handle refresh button - reload the user list in place"""
        try:
            await callback_query.answer("Обновление списка...")
            
            # Get fresh user data from database
            async with db_pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    select user_id, 
                           coalesce(intro_name, '') as intro_name,
                           coalesce(intro_location, '') as intro_location,
                           coalesce(intro_description, '') as intro_description,
                           coalesce(field_of_activity, '') as field_of_activity,
                           user_telegram_link
                    from public.users
                    where finishedonboarding = true
                    and user_id != $1
                    order by intro_name asc
                    """,
                    callback_query.from_user.id
                )
            
            if not rows:
                await callback_query.message.edit_text("📋 No users available to list yet.")
                return
            
            users = [dict(row) for row in rows]
            
            # Create updated list message
            list_message = "🔍 <b>Интерактивный список пользователей</b>\n"
            list_message += f"Показано: {len(users)} пользователей\n\n"
            list_message += "✨ <b>Особенности:</b>\n"
            list_message += "• Кликабельные профили с полной информацией\n"
            list_message += "• Фотографии профилей\n"
            list_message += "• Ссылки на Telegram и LinkedIn\n"
            list_message += "• Детальное описание и навыки\n\n"
            list_message += "Нажмите на пользователя для просмотра полного профиля:\n\n"
            
            keyboard_buttons = []
            
            # Get translated messages for consistency
            from scenes import get_messages_dynamic
            messages = get_messages_dynamic(message.from_user.id)
            missing_text = messages["MISSING_FIELD"]
            
            # Helper function to get translated value
            def get_translated_value(value, fallback=missing_text):
                if not value or value in ['Not specified', 'Not specifie', 'No description', 'No name', 'No location', 'No field of activity', 'No hobbies']:
                    return fallback
                return value
            
            for i, user in enumerate(users, 1):
                name = get_translated_value(user['intro_name'])
                location = get_translated_value(user['intro_location'])
                field_of_activity = get_translated_value(user['field_of_activity'])
                
                # Extract country from location
                country = location.split(',')[-1].strip() if ',' in location else location
                
                # Use field of activity directly
                sphere = field_of_activity
                
                # Create button text (limited to 64 chars for Telegram)
                if sphere == missing_text:
                    sphere_display = missing_text
                else:
                    sphere_display = sphere[:12]
                
                button_text = f"{i}. {name[:18]} | {sphere_display} | {country[:12]}"
                if len(button_text) > 60:
                    if sphere == missing_text:
                        sphere_display = missing_text
                    else:
                        sphere_display = sphere[:10]
                    button_text = f"{i}. {name[:15]} | {sphere_display} | {country[:10]}"
                
                # Add button for each user
                keyboard_buttons.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"browse_user_{user['user_id']}"
                )])
            
            # Add navigation and utility buttons
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_user_list")
            ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Закрыть", callback_data="close_user_list")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Update the message with fresh data
            await callback_query.message.edit_text(list_message, parse_mode="HTML", reply_markup=keyboard)
            
        except Exception as e:
            await callback_query.answer("Ошибка при обновлении списка")
            logger.error(f"Error in handle_refresh_user_list: {e}")

    @dp.callback_query(F.data == "close_user_list")
    async def handle_close_user_list(callback_query, state: FSMContext):
        """Handle close button"""
        await callback_query.message.delete()
        await callback_query.answer()

    async def show_browse_profile(message: Message, user_info: dict, current_index: int, total_users: int, state: FSMContext = None):
        """Show a user profile in browse mode"""
        from scenes import get_messages_dynamic, build_profile_text
        
        print(f"DEBUG: show_browse_profile called for user: {user_info.get('intro_name', 'Unknown')}")
        print(f"DEBUG: User has image: {bool(user_info.get('intro_image'))}")
        if user_info.get("intro_image"):
            print(f"DEBUG: Image data preview: {user_info['intro_image'][:100]}...")
        
        # Note: Removed deletion of previous messages to improve navigation speed
        # Previous photo and text messages will remain on screen during navigation
        
        photo_message_id = None
        
        # Send photo first if available
        if user_info.get("intro_image"):
            print(f"DEBUG: Processing image data: {user_info['intro_image'][:100]}...")
            try:
                import base64
                import aiohttp
                from aiogram.types import BufferedInputFile
                
                image_data = user_info["intro_image"]
                print(f"DEBUG: Image data type: {type(image_data)}, length: {len(image_data) if image_data else 0}")
                
                # Handle different image formats
                if image_data.startswith('data:image/'):
                    print(f"DEBUG: Processing data URL format")
                    # Data URL format - extract base64 part
                    base64_data = image_data.split(',')[1]
                    photo_data = base64.b64decode(base64_data)
                elif image_data.startswith(('http://', 'https://')):
                    print(f"DEBUG: Processing URL format: {image_data}")
                    # URL format - download and convert to base64
                    
                    # Check if it's ui-avatars.com and modify URL to request PNG format
                    if 'ui-avatars.com' in image_data and 'format=' not in image_data:
                        image_data = image_data + '&format=png'
                        print(f"DEBUG: Modified URL to request PNG: {image_data}")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_data) as response:
                            if response.status == 200:
                                photo_data = await response.read()
                                content_type = response.headers.get('content-type', 'unknown')
                                print(f"DEBUG: Downloaded image data, size: {len(photo_data)} bytes")
                                print(f"DEBUG: Image content type: {content_type}")
                                
                                # Check if it's SVG and skip if so
                                if 'svg' in content_type.lower() or photo_data.startswith(b'<svg'):
                                    print(f"DEBUG: Skipping SVG image (not supported by Telegram)")
                                    return
                            else:
                                print(f"DEBUG: Failed to download image from URL: {response.status}")
                                return
                else:
                    print(f"DEBUG: Processing as raw base64 data")
                    # Assume it's raw base64 data
                    photo_data = base64.b64decode(image_data)
                
                print(f"DEBUG: About to send photo, data size: {len(photo_data)} bytes")
                input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                photo_message = await message.answer_photo(input_file)
                photo_message_id = photo_message.message_id
                print(f"DEBUG: Photo sent successfully, message ID: {photo_message_id}")
            except Exception as photo_error:
                print(f"DEBUG: Error sending photo: {photo_error}")
                # Continue without photo if there's an error
        
        # Store photo message ID in state for cleanup
        if state and photo_message_id:
            await state.update_data(browse_photo_message_id=photo_message_id)
        
        # Build profile text using new format
        profile_text = build_profile_text(user_info, message.from_user.id, is_own_profile=False)
        
        # Send text-only profile
        keyboard = await get_browse_keyboard(
            has_next=current_index < total_users - 1,
            has_previous=current_index > 0
        )
        text_message = await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")
        
        # Store the text message ID in state for cleanup
        if state:
            await state.update_data(browse_text_message_id=text_message.message_id)

    async def get_my_matches_keyboard(has_next: bool = True) -> InlineKeyboardMarkup:
        """Get keyboard for my matches"""
        buttons = []
        
        if has_next:
            buttons.append([InlineKeyboardButton(
                text="Следующий",
                callback_data="my_matches_next"
            )])
        
        buttons.append([
            InlineKeyboardButton(
                text="Все пользователи",
                callback_data="my_matches_browse"
            ),
            InlineKeyboardButton(
                text="Выход",
                callback_data="my_matches_exit"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def get_browse_keyboard(has_next: bool = True, has_previous: bool = True) -> InlineKeyboardMarkup:
        """Get keyboard for browse functionality"""
        buttons = []
        
        row = []
        if has_previous:
            row.append(InlineKeyboardButton(
                text="Предыдущий",
                callback_data="browse_previous"
            ))
        if has_next:
            row.append(InlineKeyboardButton(
                text="Следующий",
                callback_data="browse_next"
            ))
        
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton(
            text="Выход",
            callback_data="browse_exit"
        )])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Start the scheduler
    await start_scheduler()
    
    try:
        await dp.start_polling(bot)
    finally:
        # Stop the scheduler when the bot stops
        await stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())


