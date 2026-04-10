import asyncio
import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
import asyncpg
from db import get_pool, get_matchable_users, create_meetings, get_meeting_by_users, is_user_blocked, get_user_language, has_recent_meeting
from match_generation import cosine_similarity
from throttling import send_message_throttled
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logger = logging.getLogger(__name__)

class MatchSystem:
    def __init__(self, bot: Bot, db_pool: asyncpg.Pool):
        self.bot = bot
        self.db_pool = db_pool
        self.min_similarity_threshold = 0.3  # Minimum similarity for matches
        
    async def generate_and_create_matches(self) -> List[Tuple[int, int, str]]:
        """Generate matches and create meeting records in the database
        Returns list of tuples: (user1_id, user2_id, meeting_id)"""
        logger.info("Starting automatic match generation...")
        
        # Get all matchable users
        users = await get_matchable_users(self.db_pool)
        
        if len(users) < 2:
            logger.info("Not enough users to generate matches")
            return []
        
        # Generate user pairs using greedy matching algorithm
        pairs = await self._generate_user_pairs(users)
        
        if not pairs:
            logger.info("No suitable pairs found for matching")
            return []
        
        # Create meeting records in database
        meeting_ids = await create_meetings(self.db_pool, pairs)
        
        # Combine pairs with meeting_ids
        pairs_with_ids = [(pair[0], pair[1], meeting_id) for pair, meeting_id in zip(pairs, meeting_ids)]
        
        logger.info(f"Created {len(meeting_ids)} new meetings")
        return pairs_with_ids
    
    async def _generate_user_pairs(self, users: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """Generate user pairs using greedy matching algorithm"""
        if len(users) < 2:
            return []
        
        # Create similarity matrix
        n = len(users)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                if (users[i].get("vector_description") and 
                    users[j].get("vector_description")):
                    
                    # Check if users have blocked each other
                    user_i_id = users[i]["user_id"]
                    user_j_id = users[j]["user_id"]
                    
                    if (await is_user_blocked(self.db_pool, user_i_id, user_j_id) or
                        await is_user_blocked(self.db_pool, user_j_id, user_i_id)):
                        # Skip this pair if either user has blocked the other
                        similarity_matrix[i][j] = -1
                        similarity_matrix[j][i] = -1
                        continue
                    
                    # Check if users had a completed meeting within the last 6 months
                    if await has_recent_meeting(self.db_pool, user_i_id, user_j_id, months=6):
                        # Skip this pair if they had a meeting marked as 'met' within last 6 months
                        similarity_matrix[i][j] = -1
                        similarity_matrix[j][i] = -1
                        logger.debug(f"Skipping pair {user_i_id}-{user_j_id}: recent meeting within 6 months")
                        continue
                    
                    similarity = cosine_similarity(
                        users[i]["vector_description"],
                        users[j]["vector_description"]
                    )
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
        
        # Greedy matching algorithm
        pairs = []
        used_indices = set()
        
        # Find the best pairs
        while len(used_indices) < n - 1:
            best_similarity = -1
            best_pair = None
            
            for i in range(n):
                if i in used_indices:
                    continue
                for j in range(i + 1, n):
                    if j in used_indices:
                        continue
                    
                    similarity = similarity_matrix[i][j]
                    if similarity > best_similarity and similarity >= self.min_similarity_threshold:
                        best_similarity = similarity
                        best_pair = (i, j)
            
            if best_pair is None:
                break
            
            pairs.append((users[best_pair[0]]["user_id"], users[best_pair[1]]["user_id"]))
            used_indices.add(best_pair[0])
            used_indices.add(best_pair[1])
        
        logger.info(f"Generated {len(pairs)} user pairs")
        return pairs
    
    async def notify_matches(self, pairs_with_ids: List[Tuple[int, int, str]]) -> None:
        """Send match notifications to users
        pairs_with_ids: List of tuples (user1_id, user2_id, meeting_id)"""
        for user1_id, user2_id, meeting_id in pairs_with_ids:
            try:
                await self._notify_match_pair(user1_id, user2_id, meeting_id)
            except Exception as e:
                logger.error(f"Failed to notify match between {user1_id} and {user2_id}: {e}")
    
    async def _notify_match_pair(self, user1_id: int, user2_id: int, meeting_id: str) -> None:
        """Notify a pair of users about their match"""
        # Get user information
        user1_info = await self._get_user_info(user1_id)
        user2_info = await self._get_user_info(user2_id)
        
        if not user1_info or not user2_info:
            logger.error(f"Could not get user info for {user1_id} or {user2_id}")
            return
        
        # Send notifications to both users with meeting_id
        await self._send_match_notification(user1_id, user1_info, user2_info, meeting_id, user2_id)
        await self._send_match_notification(user2_id, user2_info, user1_info, meeting_id, user1_id)
    
    async def _get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information from database"""
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT user_id, intro_name, intro_location, intro_description, 
                       intro_linkedin, intro_image, user_telegram_link, intro_hobbies_drivers, intro_skills
                FROM public.users 
                WHERE user_id = $1 AND finishedonboarding = true
                """,
                user_id
            )
            return dict(row) if row else None
    
    async def _send_match_notification(self, user_id: int, user_info: Dict[str, Any], match_info: Dict[str, Any], meeting_id: str, match_user_id: int) -> None:
        """Send match notification to a user"""
        try:
            # Import messages dynamically
            import sys
            sys.path.append('/app')
            from scenes import get_messages_dynamic
            
            # Get user language early for proper message formatting
            import os
            bot_language = os.getenv("BOT_LANGUAGE", "")
            user_lang_db = await get_user_language(self.db_pool, user_id)
            # Use BOT_LANGUAGE if set, otherwise use user's language from DB
            user_lang = bot_language if bot_language else user_lang_db
            
            messages = get_messages_dynamic()
            match_msgs = messages.get("MATCH_NOTIFICATIONS", {})
            
            # Build complete notification message (all text in one message)
            matched_with_msg = match_msgs.get('MATCHED_WITH', 'Meet {name}! 👋')
            location_msg = match_msgs.get('LOCATION', '📍 Based in: {location}')
            description_msg = match_msgs.get('DESCRIPTION', '💼 About: {description}')
            
            # Get match user name and make it clickable if Telegram link is available
            match_name = match_info.get('intro_name', messages.get('MISSING_FIELD', 'Someone'))
            match_telegram_link = match_info.get('user_telegram_link')
            
            # Format name as clickable link if Telegram is available
            if match_telegram_link:
                # Remove @ if present and create clickable link
                telegram_username = match_telegram_link.replace('@', '')
                name_display = f'<a href="https://t.me/{telegram_username}">{match_name}</a>'
            else:
                name_display = f'<b>{match_name}</b>'
            
            # Complete message with all information and next steps
            about_them_default = "<b>Here's what we know about them:</b>"
            complete_message = (
                f"{match_msgs.get('NEW_MATCH_TITLE', '🎯 <b>Great news! We found someone interesting for you</b>')}\n\n"
                f"{matched_with_msg.format(name=name_display)}\n\n"
                f"{match_msgs.get('ABOUT_THEM', about_them_default)}\n"
                f"{location_msg.format(location=match_info.get('intro_location', messages.get('MISSING_FIELD', 'Not specified')))}\n"
                f"{description_msg.format(description=match_info.get('intro_description', messages.get('MISSING_FIELD', 'No description')))}\n"
            )
            
            # Add LinkedIn link if available
            if match_info.get('intro_linkedin'):
                linkedin = match_info['intro_linkedin']
                # Ensure LinkedIn URL is properly formatted
                if not linkedin.startswith('http'):
                    linkedin_url = f"https://www.linkedin.com/in/{linkedin}" if not linkedin.startswith('/') else f"https://www.linkedin.com{linkedin}"
                else:
                    linkedin_url = linkedin
                linkedin_msg = match_msgs.get('LINKEDIN', '🔗 <b>LinkedIn:</b> {linkedin}')
                # Extract display name from LinkedIn URL if it's a full URL
                linkedin_display = linkedin.split('/')[-1] if '/' in linkedin else linkedin
                linkedin_display = linkedin_display.replace('in/', '').replace('@', '')
                complete_message += f"{linkedin_msg.format(linkedin=linkedin_display, linkedin_url=linkedin_url)}\n"
            
            # Profile link removed - will use inline button instead
            
            # Add next steps
            next_steps_default = "<b>Next Steps:</b>"
            complete_message += (
                f"\n{match_msgs.get('NEXT_STEPS', next_steps_default)}\n"
                f"{match_msgs.get('STEP_1', '💬 Contact via Telegram')}\n"
                f"{match_msgs.get('STEP_2', '☕ Schedule a meeting')}\n"
                f"{match_msgs.get('STEP_3', '🤝 Explore collaboration opportunities')}\n"
            )
            
            # Add telegram contact if available
            if match_info.get('user_telegram_link'):
                telegram_contact_msg = match_msgs.get('TELEGRAM_CONTACT', '💬 <b>Telegram:</b> <a href="https://t.me/{telegram_link}">@{telegram_link}</a>')
                complete_message += f"\n{telegram_contact_msg.format(telegram_link=match_info['user_telegram_link'])}\n"
            
            # Add tip about viewing matches later (profile link will be inserted before this if public URL)
            complete_message += (
                f"\n{match_msgs.get('VIEW_MATCHES_LATER', '<i>View all connections: /my_matches</i>')}\n\n"
                f"{match_msgs.get('SUCCESS_MESSAGE', 'Best of luck with your networking! 🚀')}"
            )
            
            # Check if matches are disabled for this user
            async with self.db_pool.acquire() as conn:
                user_row = await conn.fetchrow(
                    "SELECT matches_disabled FROM users WHERE user_id = $1",
                    user_id
                )
                matches_disabled = user_row['matches_disabled'] if user_row else False
            
            # Create inline keyboard with buttons (business-oriented)
            # user_lang already determined above
            
            if user_lang == 'ru':
                button_met = "✅ Встреча состоялась"
                button_block = "🚫 Исключить контакт"
                button_disable = "⛔ Отключить рекомендации"
                button_enable = "🔄 Включить рекомендации"
                button_profile = "👤 Открыть профиль"
            else:
                button_met = "✅ Meeting completed"
                button_block = "🚫 Exclude contact"
                button_disable = "⛔ Disable recommendations"
                button_enable = "🔄 Enable recommendations"
                button_profile = "👤 View Profile"
            
            # Build frontend profile URL for text link
            import os
            frontend_url = os.getenv("VITE_API_BASE_URL", "").replace("/api", "").rstrip("/")
            if not frontend_url:
                frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
            
            # Check if frontend URL is public (not localhost)
            is_public_url = frontend_url and not any(host in frontend_url.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0'])
            
            # Create profile URL - encode # as %23 for Telegram
            profile_url = None
            if frontend_url:
                if "/api" in frontend_url or ":8055" in frontend_url:
                    base_url = frontend_url.replace("/api", "").replace(":8055", ":8081")
                    profile_url = f"{base_url}/%23/user/{match_user_id}"
                else:
                    profile_url = f"{frontend_url}/%23/user/{match_user_id}"
            
            # Add profile link to message text if we have a public URL, otherwise use callback
            if profile_url and is_public_url:
                # Use URL link in text for public URLs
                if user_lang == 'ru':
                    profile_link_text = f"👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>\n"
                else:
                    profile_link_text = f"👤 <b>Full Profile:</b> <a href=\"{profile_url}\">View Profile</a>\n"
                # Insert profile link before "View all connections" line
                complete_message = complete_message.replace(
                    f"\n{match_msgs.get('VIEW_MATCHES_LATER', '<i>View all connections: /my_matches</i>')}",
                    f"\n{profile_link_text}{match_msgs.get('VIEW_MATCHES_LATER', '<i>View all connections: /my_matches</i>')}"
                )
            
            # TMA button — "Open in App" if TMA_URL is configured
            tma_url = os.getenv("TMA_URL", "").rstrip("/")
            tma_button_label = "📱 Открыть в приложении" if user_lang == 'ru' else "📱 Open in App"

            # Create keyboard with one button per row for better readability
            keyboard_buttons = []

            if tma_url:
                # Primary button: open TMA directly to this match
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=tma_button_label,
                        web_app=WebAppInfo(url=f"{tma_url}/match/{meeting_id}"),
                    )
                ])
            elif not (profile_url and is_public_url):
                # Fallback to callback if no TMA and no public URL
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_profile, callback_data=f"view_profile_{match_user_id}"),
                ])
            
            # Action buttons - one per row
            keyboard_buttons.append([
                InlineKeyboardButton(text=button_met, callback_data=f"match_met_{meeting_id}"),
            ])
            keyboard_buttons.append([
                InlineKeyboardButton(text=button_block, callback_data=f"match_block_{meeting_id}_{match_user_id}"),
            ])
            # Show "Enable" or "Disable" button based on current status
            if matches_disabled:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_enable, callback_data=f"match_enable_{meeting_id}"),
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_disable, callback_data=f"match_disable_{meeting_id}"),
                ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Send complete message with keyboard
            try:
                await send_message_throttled(user_id, complete_message, reply_markup=keyboard, parse_mode="HTML")
                logger.info(f"Complete notification message sent to user {user_id}")
            except Exception as e:
                if "chat not found" in str(e).lower():
                    logger.warning(f"User {user_id} not found in Telegram (possibly test user): {e}")
                else:
                    logger.error(f"Failed to send complete message to user {user_id}: {e}")
                raise
            
            # Send profile photo with simple caption (second message)
            if match_info.get('intro_image'):
                try:
                    # Convert image data to bytes and send as photo
                    import base64
                    import aiohttp
                    from aiogram.types import BufferedInputFile
                    
                    image_data = match_info['intro_image']
                    
                    # Handle different image formats
                    if image_data.startswith('data:image/'):
                        # Data URL format - extract base64 part
                        base64_data = image_data.split(',')[1]
                        image_bytes = base64.b64decode(base64_data)
                    elif image_data.startswith(('http://', 'https://')):
                        # URL format - download and convert to bytes
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_data) as response:
                                if response.status == 200:
                                    image_bytes = await response.read()
                                else:
                                    logger.warning(f"Failed to download image from URL: {response.status}")
                                    return
                    else:
                        # Assume it's raw base64 data
                        image_bytes = base64.b64decode(image_data)
                    
                    # Create BufferedInputFile for Telegram
                    photo_file = BufferedInputFile(
                        file=image_bytes,
                        filename="profile_photo.jpg"
                    )
                    
                    # Send photo with clickable name caption
                    partner_name = match_info.get('intro_name', 'Business Partner')
                    telegram_link = match_info.get('user_telegram_link', '')
                    
                    if telegram_link:
                        # Create clickable link to Telegram profile
                        photo_caption = f"📸 <a href=\"https://t.me/{telegram_link}\">{partner_name}</a>"
                    else:
                        # Fallback without link
                        photo_caption = f"📸 {partner_name}"
                    
                    await self.bot.send_photo(user_id, photo_file, caption=photo_caption, parse_mode="HTML")
                    logger.info(f"Photo sent successfully to user {user_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to send photo to user {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to send match notification to user {user_id}: {e}")
    
    async def run_automatic_matching(self) -> None:
        """Run the complete automatic matching process"""
        try:
            # Generate matches
            pairs = await self.generate_and_create_matches()
            
            if pairs:
                # Notify users about matches
                await self.notify_matches(pairs)
                logger.info(f"Successfully processed {len(pairs)} matches")
            else:
                logger.info("No new matches generated")
                
        except Exception as e:
            logger.error(f"Error in automatic matching: {e}")

# Global match system instance
_match_system: Optional[MatchSystem] = None

def init_match_system(bot: Bot, db_pool: asyncpg.Pool):
    """Initialize the global match system"""
    global _match_system
    _match_system = MatchSystem(bot, db_pool)

async def run_automatic_matching():
    """Run automatic matching using the global match system"""
    if _match_system is None:
        raise RuntimeError("Match system not initialized. Call init_match_system() first.")
    
    await _match_system.run_automatic_matching()
