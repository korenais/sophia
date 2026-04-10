import logging
import os
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

# Load environment variables early to ensure BOT_LANGUAGE is available
load_dotenv()

logger = logging.getLogger(__name__)

class PrivateChatOnlyMiddleware(BaseMiddleware):
    """Middleware to restrict bot usage to private chats only"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            # Allow only private chats
            if event.chat.type != "private":
                logger.warning(f"Bot command received in non-private chat: {event.chat.type}")
                await event.answer("This bot can only be used in private chats.")
                return
        
        return await handler(event, data)

class NoBotsMiddleware(BaseMiddleware):
    """Middleware to prevent bot-to-bot interactions"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            # Skip if message is from a bot
            if event.from_user and event.from_user.is_bot:
                logger.warning(f"Message received from bot user: {event.from_user.id}")
                return
        
        return await handler(event, data)

class GroupMembershipMiddleware(BaseMiddleware):
    """Middleware to check group membership for certain commands"""
    
    def __init__(self, group_id: str = None):
        self.group_id = group_id
        # Populate test users from environment (comma-separated list of IDs)
        test_users_env = os.getenv("TEST_USERS", "")
        try:
            self.test_users = [int(x.strip()) for x in test_users_env.split(",") if x.strip()]
        except Exception:
            logger.warning("Invalid TEST_USERS format; expected comma-separated integers")
            self.test_users = []
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            
            # Skip group membership check for test users
            if user_id in self.test_users:
                return await handler(event, data)
            
            # Skip if no group ID is configured
            if not self.group_id:
                logger.warning("TELEGRAM_GROUP_ID not set, skipping group membership check")
                return await handler(event, data)
            
            try:
                # Check if user is a member of the required group
                chat_member = await event.bot.get_chat_member(self.group_id, user_id)
                
                # Check if user is in the group
                user_in_group = (
                    chat_member.status in ["creator", "administrator", "member"] or
                    (hasattr(chat_member, 'is_member') and chat_member.is_member)
                )
                
                if not user_in_group:
                    logger.warning(f"User {user_id} is not in required group")
                    await event.answer(
                        "You need to be a member of our group to use this bot. "
                        "Please join the group first and try again."
                    )
                    return
                
            except Exception as error:
                logger.error(f"Error checking group membership for user {user_id}: {error}")
                # Continue with the request to avoid blocking users due to API errors
        
        return await handler(event, data)

class UpdateUserInteractionMiddleware(BaseMiddleware):
    """Middleware to update user's last interaction timestamp and migrate temporary user IDs"""
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user and self.db_pool:
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
            
            # Check if user exists with real user_id
            try:
                async with self.db_pool.acquire() as conn:
                    existing_user = await conn.fetchrow(
                        "SELECT user_id FROM users WHERE user_id = $1",
                        user_id
                    )
                    
                    # If user doesn't exist with real ID, try to find temporary user
                    if not existing_user:
                        temp_user = None
                        
                        # First try: match by username (case-insensitive)
                        if username:
                            temp_user = await conn.fetchrow(
                                "SELECT user_id, finishedonboarding, state, intro_name, user_telegram_link FROM users WHERE user_id < 0 AND LOWER(user_telegram_link) = LOWER($1)",
                                username
                            )
                            logger.debug(f"Checking for temp user by username '{username}': {'found' if temp_user else 'not found'}")
                        
                        # Second try: match by name (if username didn't match)
                        # intro_name в базе содержит полное имя (например "Антон Анисимов")
                        # Сравниваем с first_name + last_name из Telegram
                        if not temp_user and first_name:
                            telegram_full_name = f"{first_name} {last_name}".strip() if last_name else first_name
                            # Ищем совпадение: либо intro_name содержит имя из Telegram, либо наоборот
                            # Используем ILIKE для case-insensitive поиска
                            temp_user = await conn.fetchrow(
                                "SELECT user_id, finishedonboarding, state, intro_name, user_telegram_link FROM users WHERE user_id < 0 AND (intro_name ILIKE $1 OR $2 ILIKE '%' || TRIM(intro_name) || '%')",
                                f"%{telegram_full_name}%", telegram_full_name
                            )
                            logger.debug(f"Checking for temp user by name '{telegram_full_name}': {'found' if temp_user else 'not found'}")
                        
                        if temp_user:
                            logger.info(f"Found temporary user {temp_user['user_id']} (username: {temp_user.get('user_telegram_link')}, name: {temp_user.get('intro_name')}) for Telegram user {user_id} (username: {username}), migrating...")
                            # Migrate temporary user to real user_id, preserving finishedonboarding and state
                            finishedonboarding_value = temp_user.get('finishedonboarding', True)
                            state_value = temp_user.get('state', 'ACTIVE')
                            
                            await conn.execute(
                                "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                                user_id, temp_user['user_id'], finishedonboarding_value, state_value
                            )
                            
                            # Update telegram link if it changed
                            if username and username != temp_user.get('user_telegram_link'):
                                await conn.execute(
                                    "UPDATE users SET user_telegram_link = $1 WHERE user_id = $2",
                                    username, user_id
                                )
                                logger.info(f"Updated user_telegram_link from '{temp_user.get('user_telegram_link')}' to '{username}'")
                            
                            # Also migrate feedbacks if any
                            feedback_count = await conn.fetchval(
                                "SELECT COUNT(*) FROM feedbacks WHERE user_id = $1",
                                temp_user['user_id']
                            )
                            if feedback_count > 0:
                                await conn.execute(
                                    "UPDATE feedbacks SET user_id = $1 WHERE user_id = $2",
                                    user_id, temp_user['user_id']
                                )
                                logger.info(f"Migrated {feedback_count} feedback record(s) for user")
                            
                            logger.info(f"✓ Successfully migrated user from {temp_user['user_id']} to {user_id} (finishedonboarding={finishedonboarding_value}, state={state_value})")
                        else:
                            logger.debug(f"No temporary user found for Telegram user {user_id} (username: {username}, name: {first_name} {last_name})")
            except Exception as e:
                logger.error(f"Error in UpdateUserInteractionMiddleware for user {user_id}: {e}", exc_info=True)
                # Don't block the request if migration fails
        
        return await handler(event, data)

class BlockBotCommandsInSceneMiddleware(BaseMiddleware):
    """Middleware to block bot commands when user is in a scene"""
    
    # Commands that should always be allowed
    ALLOWED_COMMANDS = {'/help', '/topic_id', '/cancel', '/set_dynamic_menu'}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text:
            # Check if message is a bot command
            if event.text.startswith('/'):
                # Check if user is in a scene
                state: FSMContext = data.get('state')
                if state:
                    current_state = await state.get_state()
                    if current_state and current_state != "default":
                        # Allow certain commands
                        command = event.text.split()[0].lower()
                        if command in self.ALLOWED_COMMANDS:
                            logger.info(f"Allowing command {event.text} for user {event.from_user.id} in scene {current_state}")
                        elif current_state in ["ProfileStates:viewing_profile", "MyMatchesStates:viewing_matches", "BrowseStates:browsing_users"]:
                            # For viewing states, just clear the state and allow the command
                            await state.clear()
                            logger.info(f"Clearing {current_state} state for user {event.from_user.id} to allow command {event.text}")
                        else:
                            # Show current progress and ask what to do
                            await self._show_progress_and_ask_decision(event, state, current_state)
                            return
        
        return await handler(event, data)
    
    async def _show_progress_and_ask_decision(self, event: Message, state: FSMContext, current_state: str):
        """Show current progress and ask user what to do"""
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        import os
        
        # Get current data to show progress
        data = await state.get_data()
        
        # Check language preference
        lang = os.getenv("BOT_LANGUAGE", "ru").lower()
        
        if lang == "ru":
            # Russian messages
            progress_msg = "У вас есть незавершенное действие:\n\n"
            
            state_descriptions = {
                "OnboardingStates:waiting_for_name": "Ввод имени",
                "OnboardingStates:waiting_for_location": "Установка местоположения", 
                "OnboardingStates:waiting_for_description": "Написание описания",
                "OnboardingStates:waiting_for_linkedin": "Добавление LinkedIn профиля",
                "OnboardingStates:waiting_for_hobbies_drivers": "Описание хобби и мотивации",
                "OnboardingStates:waiting_for_skills": "Перечисление навыков",
                "OnboardingStates:waiting_for_birthday": "Установка дня рождения",
                "OnboardingStates:waiting_for_photo": "Загрузка фотографии",
                "OnboardingStates:partial_onboarding_confirmation": "Подтверждение профиля",
                "ProfileStates:viewing_profile": "Просмотр профиля",
                "ProfileStates:editing_profile": "Редактирование профиля"
            }
            
            current_action = state_descriptions.get(current_state, "Завершение профиля")
            progress_msg += f"Текущий шаг: {current_action}\n\n"
            
            if data:
                progress_msg += "Что вы уже ввели:\n"
                if data.get('name'):
                    progress_msg += f"✓ Имя: {data['name']}\n"
                if data.get('location'):
                    progress_msg += f"✓ Местоположение: {data['location']}\n"
                if data.get('description'):
                    progress_msg += f"✓ Описание: {data['description'][:50]}...\n" if len(data['description']) > 50 else f"✓ Описание: {data['description']}\n"
                if data.get('linkedin'):
                    progress_msg += f"✓ LinkedIn: {data['linkedin']}\n"
                if data.get('hobbies_drivers'):
                    progress_msg += f"✓ Хобби: {data['hobbies_drivers'][:30]}...\n" if len(data['hobbies_drivers']) > 30 else f"✓ Хобби: {data['hobbies_drivers']}\n"
                if data.get('skills'):
                    progress_msg += f"✓ Навыки: {data['skills'][:30]}...\n" if len(data['skills']) > 30 else f"✓ Навыки: {data['skills']}\n"
                if data.get('birthday'):
                    progress_msg += f"✓ День рождения: {data['birthday']}\n"
                if data.get('photo_base64'):
                    progress_msg += "✓ Фото: Загружено\n"
            
            progress_msg += "\nЧто вы хотите сделать?"
            
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Продолжить с того места")],
                    [KeyboardButton(text="Начать заново")],
                    [KeyboardButton(text="Отменить и выйти")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        else:
            # English messages
            progress_msg = "You have an incomplete action:\n\n"
            
            state_descriptions = {
                "OnboardingStates:waiting_for_name": "Entering your name",
                "OnboardingStates:waiting_for_location": "Setting your location", 
                "OnboardingStates:waiting_for_description": "Writing your description",
                "OnboardingStates:waiting_for_linkedin": "Adding LinkedIn profile",
                "OnboardingStates:waiting_for_hobbies_drivers": "Describing hobbies and motivation",
                "OnboardingStates:waiting_for_skills": "Listing your skills",
                "OnboardingStates:waiting_for_birthday": "Setting your birthday",
                "OnboardingStates:waiting_for_photo": "Uploading your photo",
                "OnboardingStates:partial_onboarding_confirmation": "Confirming your profile",
                "ProfileStates:viewing_profile": "Viewing your profile",
                "ProfileStates:editing_profile": "Editing your profile"
            }
            
            current_action = state_descriptions.get(current_state, "Completing your profile")
            progress_msg += f"Current step: {current_action}\n\n"
            
            if data:
                progress_msg += "What you've entered so far:\n"
                if data.get('name'):
                    progress_msg += f"✓ Name: {data['name']}\n"
                if data.get('location'):
                    progress_msg += f"✓ Location: {data['location']}\n"
                if data.get('description'):
                    progress_msg += f"✓ Description: {data['description'][:50]}...\n" if len(data['description']) > 50 else f"✓ Description: {data['description']}\n"
                if data.get('linkedin'):
                    progress_msg += f"✓ LinkedIn: {data['linkedin']}\n"
                if data.get('hobbies_drivers'):
                    progress_msg += f"✓ Hobbies: {data['hobbies_drivers'][:30]}...\n" if len(data['hobbies_drivers']) > 30 else f"✓ Hobbies: {data['hobbies_drivers']}\n"
                if data.get('skills'):
                    progress_msg += f"✓ Skills: {data['skills'][:30]}...\n" if len(data['skills']) > 30 else f"✓ Skills: {data['skills']}\n"
                if data.get('birthday'):
                    progress_msg += f"✓ Birthday: {data['birthday']}\n"
                if data.get('photo_base64'):
                    progress_msg += "✓ Photo: Uploaded\n"
            
            progress_msg += "\nWhat would you like to do?"
            
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Continue where I left off")],
                    [KeyboardButton(text="Start over")],
                    [KeyboardButton(text="Cancel and exit")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        
        await event.answer(progress_msg, reply_markup=keyboard)
