import os
import logging
from typing import Dict, Set, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"

@dataclass
class CommandRestriction:
    """Configuration for command restrictions"""
    allowed_chat_types: Set[ChatType]
    allowed_topics: Set[str] = None
    custom_message: str = None

class CommandConfig:
    """Configuration manager for command restrictions"""
    
    def __init__(self):
        self.restrictions = self._load_from_env()
    
    def _load_from_env(self) -> Dict[str, CommandRestriction]:
        """Load command restrictions from environment variables"""
        restrictions = {}
        
        # DM-only commands (default)
        dm_only_commands = os.getenv("DM_ONLY_COMMANDS", 
            "start,edit_profile,view_profile,my_matches,browse,people,report_an_issue,suggest_a_feature,say,confirm_match")
        
        for command in dm_only_commands.split(","):
            command = command.strip()
            restrictions[command] = CommandRestriction(
                allowed_chat_types={ChatType.PRIVATE},
                custom_message="🔒 Эта команда доступна только в личных сообщениях с ботом."
            )
        
        # Group-only commands
        group_only_commands = os.getenv("GROUP_ONLY_COMMANDS", "thanks,stats,top")
        for command in group_only_commands.split(","):
            command = command.strip()
            restrictions[command] = CommandRestriction(
                allowed_chat_types={ChatType.GROUP, ChatType.SUPERGROUP},
                custom_message="🔒 Эта команда доступна только в групповых чатах."
            )
        
        # Topic-specific commands
        thanks_topic = os.getenv("THANKS_TOPIC_ID")
        if thanks_topic:
            restrictions["thanks"] = CommandRestriction(
                allowed_chat_types={ChatType.GROUP, ChatType.SUPERGROUP},
                allowed_topics={thanks_topic},
                custom_message="🔒 Команда /thanks доступна только в теме благодарностей."
            )
        
        # Birthday commands (only if birthday functionality is enabled)
        birthdays_enabled = os.getenv("BIRTHDAYS", "No").strip().lower()
        if birthdays_enabled in ("yes", "true", "1", "on", "enabled"):
            birthday_topic = os.getenv("BIRTHDAY_TOPIC_ID")
            if birthday_topic:
                restrictions["check_birthdays"] = CommandRestriction(
                    allowed_chat_types={ChatType.GROUP, ChatType.SUPERGROUP},
                    allowed_topics={birthday_topic},
                    custom_message="🔒 Команда /check_birthdays доступна только в теме дней рождения."
                )
        
        return restrictions
    
    def get_restriction(self, command: str) -> CommandRestriction:
        """Get restriction configuration for a command"""
        return self.restrictions.get(command)
    
    def is_allowed(self, command: str, chat_type: str, topic_id: str = None) -> tuple[bool, str]:
        """
        Check if a command is allowed in the current context
        
        Returns:
            (is_allowed, error_message)
        """
        restriction = self.get_restriction(command)
        if not restriction:
            return True, ""  # No restrictions
        
        # Check chat type
        current_chat_type = ChatType(chat_type)
        if current_chat_type not in restriction.allowed_chat_types:
            message = restriction.custom_message or f"Команда /{command} недоступна в этом типе чата."
            return False, message
        
        # Check topic restrictions (for group chats)
        if restriction.allowed_topics and chat_type in ["group", "supergroup"]:
            if topic_id is None or str(topic_id) not in restriction.allowed_topics:
                message = restriction.custom_message or f"Команда /{command} недоступна в этой теме."
                return False, message
        
        return True, ""

# Global configuration instance
command_config = CommandConfig()



