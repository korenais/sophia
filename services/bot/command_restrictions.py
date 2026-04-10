import logging
from typing import Callable, Set
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

def dm_only_required(handler: Callable) -> Callable:
    """
    Decorator to restrict a command handler to direct messages only
    
    Usage:
        @dp.message(Command("edit_profile"))
        @dm_only_required
        async def handle_edit_profile(message: Message, state: FSMContext):
            # Handler code here
    """
    async def wrapper(message: Message, *args, **kwargs):
        if message.chat.type != "private":
            logger.info(f"Blocking DM-only command in {message.chat.type} chat")
            await message.answer(
                "🔒 Эта команда доступна только в личных сообщениях с ботом.\n\n"
                "💡 Напишите боту в личные сообщения для использования этой команды.",
                reply_to_message_id=message.message_id
            )
            return
        
        return await handler(message, *args, **kwargs)
    
    return wrapper

def group_only_required(handler: Callable) -> Callable:
    """
    Decorator to restrict a command handler to group chats only
    
    Usage:
        @dp.message(Command("thanks"))
        @group_only_required
        async def handle_thanks(message: Message, state: FSMContext):
            # Handler code here
    """
    async def wrapper(message: Message, *args, **kwargs):
        if message.chat.type == "private":
            logger.info(f"Blocking group-only command in private chat")
            await message.answer(
                "🔒 Эта команда доступна только в групповых чатах.\n\n"
                "💡 Используйте эту команду в группе для взаимодействия с другими участниками.",
                reply_to_message_id=message.message_id
            )
            return
        
        return await handler(message, *args, **kwargs)
    
    return wrapper

def topic_required(allowed_topics: Set[str]) -> Callable:
    """
    Decorator to restrict a command handler to specific topics
    
    Usage:
        @dp.message(Command("thanks"))
        @topic_required({"thanks_topic", "general_topic"})
        async def handle_thanks(message: Message, state: FSMContext):
            # Handler code here
    """
    def decorator(handler: Callable) -> Callable:
        async def wrapper(message: Message, *args, **kwargs):
            if message.chat.type in ["group", "supergroup"]:
                topic_id = getattr(message, "message_thread_id", None)
                if topic_id is None or str(topic_id) not in allowed_topics:
                    logger.info(f"Blocking command - topic {topic_id} not allowed")
                    await message.answer(
                        "🔒 Эта команда доступна только в определенных темах группы.\n\n"
                        "💡 Используйте команду в соответствующей теме.",
                        reply_to_message_id=message.message_id
                    )
                    return
            
            return await handler(message, *args, **kwargs)
        
        return wrapper
    
    return decorator



