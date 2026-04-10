import asyncio
import time
from typing import Dict, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

class ThrottlingMiddleware:
    def __init__(self, bot: Bot):
        self.bot = bot
        # Global rate limiter: 30 messages per second, 1 message per 33ms
        self.global_limiter = RateLimiter(max_concurrent=1, min_time=0.033, reservoir=30, reservoir_refresh_interval=1.0)
        # Per-chat rate limiter: 1 message per second
        self.chat_limiters: Dict[int, RateLimiter] = {}
        
    async def send_message_throttled(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup] = None,
        parse_mode: Optional[str] = None
    ):
        """Send a message with throttling applied"""
        chat_limiter = self._get_chat_limiter(chat_id)
        
        # Apply both global and per-chat throttling
        await chat_limiter.acquire()
        try:
            await self.global_limiter.acquire()
            try:
                options = {}
                if reply_markup:
                    options['reply_markup'] = reply_markup
                if parse_mode:
                    options['parse_mode'] = parse_mode
                
                await self.bot.send_message(chat_id, text, **options)
            finally:
                self.global_limiter.release()
        finally:
            chat_limiter.release()
    
    def _get_chat_limiter(self, chat_id: int) -> 'RateLimiter':
        """Get or create a rate limiter for a specific chat"""
        if chat_id not in self.chat_limiters:
            self.chat_limiters[chat_id] = RateLimiter(max_concurrent=1, min_time=1.0)
        return self.chat_limiters[chat_id]

class RateLimiter:
    def __init__(self, max_concurrent: int = 1, min_time: float = 0.0, 
                 reservoir: int = None, reservoir_refresh_interval: float = None):
        self.max_concurrent = max_concurrent
        self.min_time = min_time
        self.reservoir = reservoir
        self.reservoir_refresh_interval = reservoir_refresh_interval
        
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.last_request_time = 0.0
        self.reservoir_tokens = reservoir or float('inf')
        self.last_reservoir_refresh = time.time()
        
    async def acquire(self):
        """Acquire permission to make a request"""
        await self.semaphore.acquire()
        try:
            # Check reservoir
            if self.reservoir is not None:
                await self._wait_for_reservoir()
            
            # Check minimum time between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_time:
                await asyncio.sleep(self.min_time - time_since_last)
            
            self.last_request_time = time.time()
        except Exception:
            self.semaphore.release()
            raise
    
    def release(self):
        """Release the semaphore"""
        self.semaphore.release()
    
    async def _wait_for_reservoir(self):
        """Wait for reservoir tokens to be available"""
        current_time = time.time()
        
        # Refresh reservoir if needed
        if current_time - self.last_reservoir_refresh >= self.reservoir_refresh_interval:
            self.reservoir_tokens = self.reservoir
            self.last_reservoir_refresh = current_time
        
        # Wait for tokens to be available
        while self.reservoir_tokens <= 0:
            await asyncio.sleep(0.01)  # Small delay before checking again
            current_time = time.time()
            
            # Refresh reservoir if needed
            if current_time - self.last_reservoir_refresh >= self.reservoir_refresh_interval:
                self.reservoir_tokens = self.reservoir
                self.last_reservoir_refresh = current_time
        
        self.reservoir_tokens -= 1

# Global throttling instance
_throttling_middleware: Optional[ThrottlingMiddleware] = None

def init_throttling(bot: Bot):
    """Initialize the global throttling middleware"""
    global _throttling_middleware
    _throttling_middleware = ThrottlingMiddleware(bot)

async def send_message_throttled(
    chat_id: int, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
):
    """Send a throttled message using the global throttling middleware"""
    if _throttling_middleware is None:
        raise RuntimeError("Throttling middleware not initialized. Call init_throttling() first.")
    
    await _throttling_middleware.send_message_throttled(chat_id, text, reply_markup, parse_mode)
