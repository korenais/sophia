import logging
from typing import Optional
from aiogram import Bot
from throttling import send_message_throttled

logger = logging.getLogger(__name__)

class FeedbackNotificationSystem:
    """Handles feedback notifications to admins"""
    
    def __init__(self, bot: Bot, admin_user_id: Optional[int] = None):
        self.bot = bot
        self.admin_user_id = admin_user_id
    
    async def notify_feedback(self, user_id: int, feedback_type: str, feedback_text: str, user_info: dict = None):
        """Notify admin about new feedback"""
        if not self.admin_user_id:
            logger.warning("No admin user ID configured for feedback notifications")
            return
        
        try:
            # Get user information
            if not user_info:
                user_info = await self._get_user_info(user_id)
            
            # Format notification message
            notification_text = self._format_feedback_notification(
                user_id, feedback_type, feedback_text, user_info
            )
            
            # Send notification to admin
            await send_message_throttled(self.admin_user_id, notification_text)
            
        except Exception as e:
            logger.error(f"Error sending feedback notification: {e}")
    
    async def _get_user_info(self, user_id: int) -> dict:
        """Get user information from Telegram"""
        try:
            chat_member = await self.bot.get_chat_member(user_id, user_id)
            user = chat_member.user
            
            return {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'id': user.id
            }
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {'id': user_id}
    
    def _format_feedback_notification(self, user_id: int, feedback_type: str, feedback_text: str, user_info: dict) -> str:
        """Format feedback notification message"""
        # Build user display name
        user_name = "Unknown User"
        if user_info.get('first_name'):
            user_name = user_info['first_name']
            if user_info.get('last_name'):
                user_name += f" {user_info['last_name']}"
        
        if user_info.get('username'):
            user_name += f" (@{user_info['username']})"
        
        # Format notification
        emoji = "🐛" if feedback_type == "issue" else "💡"
        type_display = "Issue Report" if feedback_type == "issue" else "Feature Suggestion"
        
        notification = f"{emoji} <b>New {type_display}</b>\n\n"
        notification += f"<b>From:</b> {user_name} (ID: {user_id})\n"
        notification += f"<b>Type:</b> {type_display}\n\n"
        notification += f"<b>Message:</b>\n{feedback_text}\n\n"
        notification += f"<i>Received at: {self._get_current_time()}</i>"
        
        return notification
    
    def _get_current_time(self) -> str:
        """Get current time as formatted string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

# Global feedback notification system
_feedback_notifier: Optional[FeedbackNotificationSystem] = None

def init_feedback_notification(bot: Bot, admin_user_id: Optional[int] = None):
    """Initialize the global feedback notification system"""
    global _feedback_notifier
    _feedback_notifier = FeedbackNotificationSystem(bot, admin_user_id)

async def notify_feedback(user_id: int, feedback_type: str, feedback_text: str, user_info: dict = None):
    """Send feedback notification using the global system"""
    if _feedback_notifier is None:
        logger.warning("Feedback notification system not initialized")
        return
    
    await _feedback_notifier.notify_feedback(user_id, feedback_type, feedback_text, user_info)
