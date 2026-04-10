import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Callable, Any, Tuple
import asyncpg
from aiogram import Bot

logger = logging.getLogger(__name__)

class ScheduledJob:
    """Represents a scheduled job"""
    
    def __init__(self, name: str, func: Callable, interval_hours: float, last_run: datetime = None):
        self.name = name
        self.func = func
        self.interval_hours = interval_hours
        self.last_run = last_run or datetime.min
        self.next_run = self.last_run + timedelta(hours=interval_hours)
        self.is_running = False
    
    def should_run(self) -> bool:
        """Check if the job should run now"""
        return datetime.now() >= self.next_run and not self.is_running
    
    def mark_completed(self):
        """Mark job as completed and schedule next run"""
        self.last_run = datetime.now()
        self.next_run = self.last_run + timedelta(hours=self.interval_hours)
        self.is_running = False

class JobScheduler:
    """Manages scheduled background jobs"""
    
    def __init__(self, bot: Bot, db_pool: asyncpg.Pool):
        self.bot = bot
        self.db_pool = db_pool
        self.jobs: List[ScheduledJob] = []
        self.running = False
        self._task = None
    
    def add_job(self, name: str, func: Callable, interval_hours: int):
        """Add a scheduled job"""
        job = ScheduledJob(name, func, interval_hours)
        self.jobs.append(job)
        logger.info(f"Added scheduled job: {name} (every {interval_hours} hours)")
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Job scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Job scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_and_run_jobs()
                await asyncio.sleep(10)  # Check every 10 seconds for faster notification delivery
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_and_run_jobs(self):
        """Check and run jobs that are due"""
        for job in self.jobs:
            if job.should_run():
                logger.info(f"Running scheduled job: {job.name}")
                job.is_running = True
                
                try:
                    await job.func()
                    job.mark_completed()
                    logger.info(f"Completed scheduled job: {job.name}")
                except Exception as e:
                    logger.error(f"Error running job {job.name}: {e}")
                    job.is_running = False
                    # Don't mark as completed on error, will retry next interval
    
    def get_job_status(self) -> dict:
        """Get status of all jobs"""
        status = {}
        for job in self.jobs:
            status[job.name] = {
                'last_run': job.last_run.isoformat() if job.last_run != datetime.min else 'Never',
                'next_run': job.next_run.isoformat(),
                'is_running': job.is_running,
                'interval_hours': job.interval_hours
            }
        return status

# Background job functions
async def cleanup_old_messages(bot: Bot, db_pool: asyncpg.Pool):
    """Clean up old bot messages (older than 30 days)"""
    logger.info("Running cleanup_old_messages job")
    
    cutoff_date = datetime.now() - timedelta(days=30)
    
    async with db_pool.acquire() as connection:
        result = await connection.execute(
            """
            DELETE FROM public.bot_messages
            WHERE created_at < $1
            """,
            cutoff_date
        )
        
        # Extract number of deleted rows from result
        deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
        logger.info(f"Cleaned up {deleted_count} old bot messages")

async def cleanup_expired_cache(bot: Bot, db_pool: asyncpg.Pool):
    """Clean up expired cache entries"""
    logger.info("Running cleanup_expired_cache job")
    
    # This would clean up any expired cache entries
    # For now, just log that it ran
    logger.info("Cache cleanup completed")

async def process_meeting_followups(bot: Bot, db_pool: asyncpg.Pool):
    """Process meeting follow-ups"""
    logger.info("Running process_meeting_followups job")
    
    try:
        from meeting_followup import process_meeting_followups
        await process_meeting_followups()
    except Exception as e:
        logger.error(f"Error in process_meeting_followups job: {e}")

async def update_user_interaction_dates(bot: Bot, db_pool: asyncpg.Pool):
    """Update user interaction dates"""
    logger.info("Running update_user_interaction_dates job")
    
    # Update last interaction date for users who have been active
    async with db_pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE public.users
            SET updated_at = NOW()
            WHERE user_id IN (
                SELECT DISTINCT user_id
                FROM public.bot_messages
                WHERE created_at > NOW() - INTERVAL '1 day'
            )
            """
        )
    
    logger.info("User interaction dates updated")

async def generate_weekly_matches(bot: Bot, db_pool: asyncpg.Pool):
    """Generate weekly matches for users who haven't been matched recently"""
    logger.info("Running generate_weekly_matches job")
    
    try:
        from match_system import run_automatic_matching
        await run_automatic_matching()
    except Exception as e:
        logger.error(f"Error in generate_weekly_matches job: {e}")

async def check_birthday_greetings(bot: Bot, db_pool: asyncpg.Pool):
    """Check for birthdays today and send greetings"""
    logger.info("Running check_birthday_greetings job")
    
    try:
        from birthday_greetings import check_and_send_birthday_greetings
        await check_and_send_birthday_greetings(bot, db_pool)
    except Exception as e:
        logger.error(f"Error in check_birthday_greetings job: {e}")

async def check_recently_updated_birthdays(bot: Bot, db_pool: asyncpg.Pool):
    """Check for users whose birthday was recently updated (last_birthday_greeting_sent = NULL)"""
    logger.debug("Running check_recently_updated_birthdays job")
    
    try:
        from birthday_greetings import check_recently_updated_birthday_greetings
        await check_recently_updated_birthday_greetings(bot, db_pool)
    except Exception as e:
        logger.error(f"Error in check_recently_updated_birthdays job: {e}")

async def send_scheduled_notifications(bot: Bot, db_pool: asyncpg.Pool):
    """Process and send scheduled notifications"""
    logger.info("Running send_scheduled_notifications job")
    
    try:
        from notifications import process_scheduled_notifications
        await process_scheduled_notifications(bot, db_pool)
    except Exception as e:
        logger.error(f"Error in send_scheduled_notifications job: {e}", exc_info=True)

# Global scheduler instance
_scheduler: JobScheduler = None

def init_scheduler(bot: Bot, db_pool: asyncpg.Pool):
    """Initialize the global scheduler with default jobs"""
    global _scheduler
    _scheduler = JobScheduler(bot, db_pool)
    
    import os
    
    # Add default jobs
    _scheduler.add_job("cleanup_old_messages", lambda: cleanup_old_messages(bot, db_pool), 24)  # Daily
    _scheduler.add_job("cleanup_expired_cache", lambda: cleanup_expired_cache(bot, db_pool), 6)  # Every 6 hours
    _scheduler.add_job("process_meeting_followups", lambda: process_meeting_followups(bot, db_pool), 12)  # Twice daily
    _scheduler.add_job("update_user_interaction_dates", lambda: update_user_interaction_dates(bot, db_pool), 1)  # Hourly
    _scheduler.add_job("generate_weekly_matches", lambda: generate_weekly_matches(bot, db_pool), 168)  # Weekly
    
    # Only add birthday job if birthday functionality is enabled
    birthdays_enabled = os.getenv("BIRTHDAYS", "No").strip().lower()
    if birthdays_enabled in ("yes", "true", "1", "on", "enabled"):
        # Check once per day (24 hours) to send birthday greetings
        _scheduler.add_job("check_birthday_greetings", lambda: check_birthday_greetings(bot, db_pool), 24)
        logger.info("Birthday greetings job enabled (BIRTHDAYS=Yes) - checking once per day")
        
        # Also check for recently updated birthdays (when admin changes birthday date)
        # Check every 5 minutes to catch admin panel updates quickly
        _scheduler.add_job("check_recently_updated_birthdays", lambda: check_recently_updated_birthdays(bot, db_pool), 5/60)
        logger.info("Recently updated birthdays job enabled - checking every 5 minutes")
    else:
        logger.info("Birthday greetings job disabled (BIRTHDAYS=No)")
    
    # Add notification sending job (check every 10 seconds for fast delivery of "send now" notifications)
    # Use async lambda to properly await the coroutine
    async def notification_job():
        await send_scheduled_notifications(bot, db_pool)
    _scheduler.add_job("send_scheduled_notifications", notification_job, interval_hours=10/3600)  # Every 10 seconds (10/3600 hours)
    logger.info("Scheduled notifications job enabled (checks every 10 seconds)")

async def start_scheduler():
    """Start the global scheduler"""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    
    await _scheduler.start()

async def stop_scheduler():
    """Stop the global scheduler"""
    if _scheduler is None:
        return
    
    await _scheduler.stop()

def get_scheduler_status() -> dict:
    """Get scheduler status"""
    if _scheduler is None:
        return {"error": "Scheduler not initialized"}
    
    return {
        "running": _scheduler.running,
        "jobs": _scheduler.get_job_status()
    }

def get_scheduler_bot_and_pool() -> Tuple[Bot, asyncpg.Pool]:
    """Get bot and db_pool from scheduler for use in other modules"""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler.bot, _scheduler.db_pool
