import logging
from typing import Callable, Dict, Any, Awaitable, Set
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class DMOnlyCommandsMiddleware(BaseMiddleware):
    """Middleware to restrict specific commands to direct messages only"""
    
    def __init__(self, dm_only_commands: Set[str] = None):
        """
        Initialize middleware with commands that should only work in DMs
        
        Args:
            dm_only_commands: Set of command names (without /) that should be DM-only
        """
        self.dm_only_commands = dm_only_commands or {
            'start', 'edit_profile', 'view_profile', 'my_matches', 'browse', 'people',
            'report_an_issue', 'suggest_a_feature', 'say', 'confirm_match'
        }
        logger.info(f"DMOnlyCommandsMiddleware initialized with commands: {self.dm_only_commands}")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        logger.info(f"🔍 DMOnlyCommandsMiddleware: Processing event type: {type(event)}")
        
        if isinstance(event, Message) and event.text:
            logger.info(f"🔍 DMOnlyCommandsMiddleware: Message text: '{event.text}', chat type: {event.chat.type}")
            
            # Check if message is a bot command
            if event.text.startswith('/'):
                command = event.text.split()[0][1:].lower()  # Remove / and get command name
                
                # Remove bot username if present (e.g., "view_profile@botname" -> "view_profile")
                if '@' in command:
                    command = command.split('@')[0]
                
                logger.warning(f"🔍 DMOnlyCommandsMiddleware: Processing command '{command}' in {event.chat.type} chat")
                
                # Check if this command should be DM-only
                if command in self.dm_only_commands:
                    logger.error(f"🔍 DMOnlyCommandsMiddleware: Command '{command}' is DM-only, checking chat type: {event.chat.type}")
                    
                    # Check if we're in a private chat
                    if event.chat.type != "private":
                        logger.error(f"🚫 DMOnlyCommandsMiddleware: BLOCKING DM-only command '{command}' in {event.chat.type} chat")
                        
                        # Send helpful message to user
                        await event.answer(
                            f"🔒 Команда /{command} доступна только в личных сообщениях с ботом.\n\n"
                            f"💡 Напишите боту в личные сообщения для использования этой команды.",
                            reply_to_message_id=event.message_id
                        )
                        return  # Block the command
                    else:
                        logger.info(f"✅ DMOnlyCommandsMiddleware: Allowing DM-only command '{command}' in private chat")
                else:
                    logger.info(f"✅ DMOnlyCommandsMiddleware: Command '{command}' is not DM-only, allowing")
        else:
            logger.info(f"🔍 DMOnlyCommandsMiddleware: Not a text message or no text, allowing through")
        
        return await handler(event, data)
