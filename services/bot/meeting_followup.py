import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncpg
from db import get_pool, get_meeting_by_id, update_meeting_status, update_meeting_followup_status
from throttling import send_message_throttled
from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)

class MeetingFollowupSystem:
    def __init__(self, bot: Bot, db_pool: asyncpg.Pool):
        self.bot = bot
        self.db_pool = db_pool
        self.followup_delay_days = 7  # Follow up after 7 days
        
    async def process_followups(self) -> None:
        """Process all meetings that need follow-up"""
        logger.info("Starting meeting follow-up process...")
        
        # Get meetings that need follow-up (7+ days old, matched status, not yet followed up)
        meetings = await self._get_meetings_needing_followup()
        
        if not meetings:
            logger.info("No meetings need follow-up")
            return
        
        logger.info(f"Found {len(meetings)} meetings needing follow-up")
        
        for meeting in meetings:
            try:
                await self._process_meeting_followup(meeting)
            except Exception as e:
                logger.error(f"Error processing follow-up for meeting {meeting['id']}: {e}")
    
    async def _get_meetings_needing_followup(self) -> List[Dict[str, Any]]:
        """Get meetings that need follow-up"""
        cutoff_date = datetime.now() - timedelta(days=self.followup_delay_days)
        
        async with self.db_pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, user_1_id, user_2_id, status, created_at, last_updated
                FROM public.meetings
                WHERE status = 'matched'
                  AND created_at <= $1
                  AND (sent_followup_message IS NULL OR sent_followup_message = false)
                ORDER BY created_at ASC
                """,
                cutoff_date
            )
            return [dict(row) for row in rows]
    
    async def _process_meeting_followup(self, meeting: Dict[str, Any]) -> None:
        """Process follow-up for a single meeting"""
        meeting_id = meeting['id']
        user1_id = meeting['user_1_id']
        user2_id = meeting['user_2_id']
        
        logger.info(f"Processing follow-up for meeting {meeting_id}")
        
        # Get user information for both users
        user1_info = await self._get_user_info(user1_id)
        user2_info = await self._get_user_info(user2_id)
        
        if not user1_info or not user2_info:
            logger.error(f"Could not get user info for meeting {meeting_id}")
            return
        
        # Send follow-up messages to both users
        await self._send_followup_message(user1_id, user2_info.get('intro_name'))
        await self._send_followup_message(user2_id, user1_info.get('intro_name'))
        
        # Update meeting status to indicate follow-up was sent
        await update_meeting_followup_status(self.db_pool, meeting_id, True)
        
        logger.info(f"Follow-up completed for meeting {meeting_id}")
    
    async def _get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information from database"""
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT user_id, intro_name, intro_location, intro_description, 
                       intro_linkedin, intro_image, user_telegram_link
                FROM public.users 
                WHERE user_id = $1 AND finishedonboarding = true
                """,
                user_id
            )
            return dict(row) if row else None
    
    async def _send_followup_message(self, user_id: int, match_name: Optional[str]) -> None:
        """Send follow-up message to a user"""
        try:
            match_name_display = match_name or "your match"
            
            followup_text = (
                f"👋 Hi! It's been a week since you were matched with {match_name_display}.\n\n"
                f"💬 <b>How did it go?</b>\n\n"
                f"Did you have a chance to connect? We'd love to hear about your experience!\n\n"
                f"Please let us know:"
            )
            
            # Create keyboard with Yes/No options
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Yes, we connected!")],
                    [KeyboardButton(text="❌ No, we didn't connect")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await send_message_throttled(user_id, followup_text, keyboard)
            
        except Exception as e:
            logger.error(f"Failed to send follow-up message to user {user_id}: {e}")
    
    async def handle_followup_response(self, user_id: int, response: str) -> None:
        """Handle user's response to follow-up message"""
        try:
            # Find the user's active meeting
            meeting = await self._get_user_active_meeting(user_id)
            
            if not meeting:
                logger.warning(f"No active meeting found for user {user_id}")
                return
            
            # Determine if the meeting was successful
            call_successful = "yes" in response.lower() or "✅" in response
            
            # Update meeting status
            await self._update_meeting_call_status(meeting['id'], call_successful)
            
            # Send thank you message
            thank_you_text = (
                "🙏 Thank you for your feedback!\n\n"
                "Your response helps us improve our matching system. "
                "We hope you had a great experience!"
            )
            
            await send_message_throttled(user_id, thank_you_text)
            
            logger.info(f"Updated meeting {meeting['id']} call status: {call_successful}")
            
        except Exception as e:
            logger.error(f"Error handling follow-up response from user {user_id}: {e}")
    
    async def _get_user_active_meeting(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active meeting that needs follow-up response"""
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT id, user_1_id, user_2_id, status, created_at, last_updated
                FROM public.meetings
                WHERE (user_1_id = $1 OR user_2_id = $1)
                  AND status = 'matched'
                  AND sent_followup_message = true
                  AND call_successful IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id
            )
            return dict(row) if row else None
    
    async def _update_meeting_call_status(self, meeting_id: str, call_successful: bool) -> None:
        """Update meeting call status"""
        async with self.db_pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE public.meetings
                SET call_successful = $2, last_updated = NOW()
                WHERE id = $1
                """,
                meeting_id, call_successful
            )

# Global followup system instance
_followup_system: Optional[MeetingFollowupSystem] = None

def init_followup_system(bot: Bot, db_pool: asyncpg.Pool):
    """Initialize the global followup system"""
    global _followup_system
    _followup_system = MeetingFollowupSystem(bot, db_pool)

async def process_meeting_followups():
    """Process meeting follow-ups using the global followup system"""
    if _followup_system is None:
        raise RuntimeError("Followup system not initialized. Call init_followup_system() first.")
    
    await _followup_system.process_followups()

async def handle_followup_response(user_id: int, response: str):
    """Handle follow-up response using the global followup system"""
    if _followup_system is None:
        raise RuntimeError("Followup system not initialized. Call init_followup_system() first.")
    
    await _followup_system.handle_followup_response(user_id, response)
