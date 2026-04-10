import asyncio
import logging
from typing import Dict, Optional, Set
import asyncpg
from datetime import datetime, timedelta
from aiogram import Bot

logger = logging.getLogger(__name__)

class UsernameCache:
    """Caches usernames to avoid repeated API calls"""
    
    def __init__(self, bot: Bot, db_pool: asyncpg.Pool, cache_ttl_hours: int = 24):
        self.bot = bot
        self.db_pool = db_pool
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache: Dict[int, Dict[str, any]] = {}
        self._lock = asyncio.Lock()
    
    async def get_username(self, user_id: int) -> Optional[str]:
        """
        Get username for a user ID, using cache if available
        """
        async with self._lock:
            # Check cache first
            if user_id in self._cache:
                cache_entry = self._cache[user_id]
                if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                    return cache_entry['username']
                else:
                    # Cache expired, remove it
                    del self._cache[user_id]
            
            # Get from database
            username = await self._get_username_from_db(user_id)
            if username:
                # Cache the result
                self._cache[user_id] = {
                    'username': username,
                    'timestamp': datetime.now()
                }
                return username
            
            # If not in database, try to get from Telegram API
            try:
                username = await self._get_username_from_telegram(user_id)
                if username:
                    # Cache and store in database
                    await self._store_username_in_db(user_id, username)
                    self._cache[user_id] = {
                        'username': username,
                        'timestamp': datetime.now()
                    }
                return username
            except Exception as e:
                logger.error(f"Error getting username from Telegram for user {user_id}: {e}")
                return None
    
    async def _get_username_from_db(self, user_id: int) -> Optional[str]:
        """Get username from database"""
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT username, username_updated_at
                FROM public.users
                WHERE user_id = $1
                """,
                user_id
            )
            
            if row and row['username']:
                # Check if username is still fresh (less than cache TTL old)
                if row['username_updated_at']:
                    age = datetime.now() - row['username_updated_at']
                    if age < self.cache_ttl:
                        return row['username']
            
            return None
    
    async def _get_username_from_telegram(self, user_id: int) -> Optional[str]:
        """Get username from Telegram API"""
        try:
            chat_member = await self.bot.get_chat_member(user_id, user_id)
            return chat_member.user.username
        except Exception as e:
            logger.warning(f"Could not get username from Telegram for user {user_id}: {e}")
            return None
    
    async def _store_username_in_db(self, user_id: int, username: str) -> None:
        """Store username in database"""
        async with self.db_pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE public.users
                SET username = $2, username_updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id, username
            )
    
    async def invalidate_cache(self, user_id: int) -> None:
        """Invalidate cache for a specific user"""
        async with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
    
    async def clear_expired_cache(self) -> None:
        """Clear expired cache entries"""
        async with self._lock:
            now = datetime.now()
            expired_users = [
                user_id for user_id, entry in self._cache.items()
                if now - entry['timestamp'] >= self.cache_ttl
            ]
            for user_id in expired_users:
                del self._cache[user_id]
    
    async def get_cached_usernames(self, user_ids: list[int]) -> Dict[int, Optional[str]]:
        """
        Get multiple usernames efficiently, using cache when possible
        """
        result = {}
        uncached_users = []
        
        async with self._lock:
            for user_id in user_ids:
                if user_id in self._cache:
                    cache_entry = self._cache[user_id]
                    if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                        result[user_id] = cache_entry['username']
                    else:
                        # Cache expired
                        del self._cache[user_id]
                        uncached_users.append(user_id)
                else:
                    uncached_users.append(user_id)
        
        # Get uncached usernames from database
        if uncached_users:
            db_usernames = await self._get_usernames_from_db(uncached_users)
            result.update(db_usernames)
            
            # Cache the results
            async with self._lock:
                for user_id, username in db_usernames.items():
                    if username:
                        self._cache[user_id] = {
                            'username': username,
                            'timestamp': datetime.now()
                        }
        
        return result
    
    async def _get_usernames_from_db(self, user_ids: list[int]) -> Dict[int, Optional[str]]:
        """Get multiple usernames from database"""
        if not user_ids:
            return {}
        
        async with self.db_pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT user_id, username, username_updated_at
                FROM public.users
                WHERE user_id = ANY($1)
                """,
                user_ids
            )
            
            result = {}
            for row in rows:
                if row['username'] and row['username_updated_at']:
                    age = datetime.now() - row['username_updated_at']
                    if age < self.cache_ttl:
                        result[row['user_id']] = row['username']
            
            return result

class UsernameHelper:
    """Helper functions for username operations"""
    
    @staticmethod
    def format_username_display(username: Optional[str], user_id: int) -> str:
        """
        Format username for display
        """
        if username:
            return f"@{username}"
        else:
            return f"User {user_id}"
    
    @staticmethod
    def is_username_mention(text: str) -> bool:
        """
        Check if text is a username mention
        """
        return text.startswith('@') and len(text) > 1
    
    @staticmethod
    def extract_username_from_mention(mention: str) -> Optional[str]:
        """
        Extract username from mention text
        """
        if not UsernameHelper.is_username_mention(mention):
            return None
        
        username = mention[1:]  # Remove @
        # Basic validation
        if len(username) >= 5 and username.replace('_', '').isalnum():
            return username
        
        return None
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """
        Normalize username (remove @, convert to lowercase)
        """
        if not username:
            return ""
        
        return username.lstrip('@').lower()

# Global username cache instance
_username_cache: Optional[UsernameCache] = None

def init_username_cache(bot: Bot, db_pool: asyncpg.Pool):
    """Initialize the global username cache"""
    global _username_cache
    _username_cache = UsernameCache(bot, db_pool)

async def get_username(user_id: int) -> Optional[str]:
    """Get username using the global cache"""
    if _username_cache is None:
        raise RuntimeError("Username cache not initialized. Call init_username_cache() first.")
    
    return await _username_cache.get_username(user_id)

async def get_cached_usernames(user_ids: list[int]) -> Dict[int, Optional[str]]:
    """Get multiple usernames using the global cache"""
    if _username_cache is None:
        raise RuntimeError("Username cache not initialized. Call init_username_cache() first.")
    
    return await _username_cache.get_cached_usernames(user_ids)

async def invalidate_username_cache(user_id: int):
    """Invalidate username cache for a user"""
    if _username_cache is None:
        return
    
    await _username_cache.invalidate_cache(user_id)
