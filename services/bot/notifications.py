"""
Notification sending system for Sophia bot
Handles scheduled and immediate notification delivery
"""
import os
import logging
import asyncio
from datetime import datetime
from typing import List, Optional
import asyncpg
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# Configure logging with debug level for detailed information
logger = logging.getLogger(__name__)
# Enable debug logging if DEBUG environment variable is set
if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


async def send_notification_to_user(
    bot: Bot,
    user_id: int,
    message_text: str,
    db_pool: asyncpg.Pool,
    image_url: str | None = None
) -> bool:
    """
    Send a notification message to a specific user
    
    Args:
        bot: Telegram bot instance
        user_id: Target user ID
        message_text: HTML-formatted message text (will be caption if image_url provided)
        db_pool: Database connection pool
        image_url: Optional image URL - if provided, sends as photo with message_text as caption
        
    Returns:
        True if sent successfully, False otherwise
    """
    logger.debug(f"[DEBUG] send_notification_to_user called: user_id={user_id}, message_length={len(message_text)}")
    try:
        # Check if user has notifications enabled
        user_name = None
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT user_id, chat_id, notifications_enabled, state, intro_name, user_telegram_link
                FROM users
                WHERE user_id = $1
                """,
                user_id
            )
            
            logger.debug(f"[DEBUG] User query result: {user}")
            
            if not user:
                logger.warning(f"User {user_id} not found in database")
                return False
            
            user_name = user.get('intro_name') or f"User {user_id}"
            
            # Check if user has Telegram link (critical for sending messages)
            user_telegram_link = user.get('user_telegram_link')
            if not user_telegram_link or user_telegram_link.strip() == '':
                logger.warning(f"User {user_id} ({user_name}) has no Telegram link, cannot send message")
                return False
            
            # Check if user_id is negative (groups have negative IDs, private chats have positive)
            if user_id < 0:
                logger.warning(f"User {user_id} ({user_name}) has negative ID (group, not private chat), cannot send message")
                return False
            
            if not user['notifications_enabled']:
                logger.info(f"Notifications disabled for user {user_id} ({user_name}), skipping")
                return False
            
            if user['state'] != 'ACTIVE':
                logger.info(f"User {user_id} ({user_name}) is not active (state: {user['state']}), skipping")
                return False
            
            chat_id = user['chat_id'] or user['user_id']
            logger.debug(f"[DEBUG] Sending to chat_id={chat_id}, image_url={image_url}")
            
        # Send the message with aggressive timeout to prevent hanging
        try:
            if image_url:
                # Send as photo with caption (caption max 1024 chars)
                logger.debug(f"[DEBUG] Attempting to send photo notification to user {user_id}, chat_id={chat_id}, image_url={image_url}")
                
                # Validate caption length (Telegram limit: 1024 chars for photo captions)
                import re
                text_without_tags = re.sub(r'<[^>]*>', '', message_text)
                if len(text_without_tags) > 1024:
                    logger.warning(f"Photo caption too long ({len(text_without_tags)} chars). Telegram limit is 1024 chars for captions.")
                    # Telegram will reject if too long, but we'll try anyway to get proper error message
                
                await asyncio.wait_for(
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=message_text,
                        parse_mode=ParseMode.HTML
                    ),
                    timeout=5.0  # 5 seconds for photo (may take longer to download)
                )
                logger.info(f"Photo notification sent successfully to user {user_id}")
                logger.debug(f"[DEBUG] Photo sent: chat_id={chat_id}, image_url={image_url}, caption_preview={message_text[:50]}...")
            else:
                # Send as regular text message (max 4096 chars)
                logger.debug(f"[DEBUG] Attempting to send text message to user {user_id}, chat_id={chat_id}")
                await asyncio.wait_for(
                    bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML
                    ),
                    timeout=3.0  # 3 second timeout per message
                )
                logger.info(f"Notification sent successfully to user {user_id}")
                logger.debug(f"[DEBUG] Message sent: chat_id={chat_id}, text_preview={message_text[:50]}...")
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending notification to user {user_id} ({user_name}): exceeded 3 seconds")
            return False
        except TelegramForbiddenError as e:
            logger.warning(f"User {user_id} ({user_name}): blocked the bot or chat not found: {e}")
            return False
        except TelegramBadRequest as e:
            error_msg = f"Failed to send notification to user {user_id} ({user_name}): {e}"
            logger.error(error_msg)
            # Only report critical notification errors (thread not found, chat not found, etc.)
            error_str = str(e).lower()
            is_critical = (
                "thread not found" in error_str or
                "chat not found" in error_str or
                "group not found" in error_str or
                "topic not found" in error_str
            )
            if is_critical:
                try:
                    from bug_reporting import report_bug
                    await report_bug(
                        error_type="notification",
                        error_message=error_msg,
                        context={
                            "user_id": user_id,
                            "error_type": type(e).__name__,
                            "has_image": image_url is not None
                        },
                        exception=e,
                        severity="critical"
                    )
                except Exception as br_e:
                    logger.warning(f"Could not create bug report: {br_e}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error sending notification to user {user_id} ({user_name}): {e}"
            logger.error(error_msg, exc_info=True)
            # Only report unexpected errors - they are likely critical
            try:
                from bug_reporting import report_bug
                await report_bug(
                    error_type="notification",
                    error_message=error_msg,
                    context={
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                        "has_image": image_url is not None
                    },
                    exception=e,
                    severity="high"
                )
            except Exception as br_e:
                logger.warning(f"Could not create bug report: {br_e}")
            return False
            
    except Exception as e:
        user_name_str = user_name if user_name else f"User {user_id}"
        logger.error(f"Error in send_notification_to_user for user {user_id} ({user_name_str}): {e}", exc_info=True)
        return False


async def send_notification(
    bot: Bot,
    notification_id: int,
    db_pool: asyncpg.Pool
) -> dict:
    """
    Send a notification to all specified recipients
    
    Args:
        bot: Telegram bot instance
        notification_id: Notification ID from database
        db_pool: Database connection pool
        
    Returns:
        Dictionary with sending statistics
    """
    logger.info(f"send_notification called for notification_id={notification_id}")
    
    # Get notification details (close connection quickly)
    logger.debug(f"Acquiring DB connection to fetch notification {notification_id}")
    async with db_pool.acquire() as conn:
        logger.debug(f"DB connection acquired, fetching notification {notification_id}")
        notification = await conn.fetchrow(
            """
            SELECT id, message_text, image_url, recipient_type, recipient_ids, status
            FROM notifications
            WHERE id = $1
            """,
            notification_id
        )
        logger.debug(f"Notification fetched: {notification}")
    
    logger.debug(f"DB connection released")
    
    if not notification:
        logger.error(f"Notification {notification_id} not found")
        return {"error": "Notification not found"}
    
    # Process notifications with status 'sent' (for immediate sending) or 'scheduled' (for scheduled sending)
    # "Send now" notifications have status 'sent' and scheduled_at = NULL
    # Scheduled notifications have status 'scheduled' and scheduled_at with a future date
    if notification['status'] == 'sent':
        # This is a "send now" notification - proceed with sending
        pass
    elif notification['status'] == 'scheduled':
        # This is a scheduled notification - proceed with sending
        pass
    else:
        logger.warning(f"Notification {notification_id} is not ready to send (status: {notification['status']})")
        return {"error": f"Notification status is '{notification['status']}', not ready to send"}
    
    message_text = notification['message_text']
    image_url = notification.get('image_url')
    recipient_type = notification['recipient_type']
    recipient_ids = notification['recipient_ids'] or []
    
    # Handle group type separately - send to configured Telegram group
    if recipient_type == 'group':
        group_chat_id = os.getenv("TELEGRAM_GROUP_ID")
        if not group_chat_id:
            logger.error(f"TELEGRAM_GROUP_ID not set, cannot send notification {notification_id} to group")
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notifications
                    SET status = 'sent', 
                        sent_at = NOW(), 
                        sent_count = 0,
                        failed_count = 1,
                        error_message = 'TELEGRAM_GROUP_ID not configured',
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    notification_id
                )
            return {"sent": 0, "failed": 1, "total": 1}
        
        # Send to group
        try:
            group_id = int(group_chat_id)
            logger.info(f"Sending notification {notification_id} to Telegram group {group_id}")
            
            if image_url:
                # Send as photo with caption
                await bot.send_photo(
                    chat_id=group_id,
                    photo=image_url,
                    caption=message_text,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Send as text message
                await bot.send_message(
                    chat_id=group_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"Notification {notification_id} sent successfully to group {group_id}")
            
            # Update notification status - group message was sent successfully
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notifications
                    SET status = 'sent', 
                        sent_at = NOW(), 
                        sent_count = 1,
                        failed_count = 0,
                        error_message = NULL,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    notification_id
                )

            logger.info(f"Group notification {notification_id} sent successfully to group {group_id}")
            return {"sent": 1, "failed": 0, "total": 1}
            
        except Exception as e:
            error_msg_full = f"Failed to send notification {notification_id} to group: {e}"
            logger.error(error_msg_full, exc_info=True)
            error_msg = f'Failed to send to group: {str(e)}'
            # Create bug report for group notification failures
            try:
                from bug_reporting import report_bug
                await report_bug(
                    error_type="notification",
                    error_message=error_msg_full,
                    context={
                        "notification_id": notification_id,
                        "recipient_type": recipient_type,
                        "error_type": type(e).__name__
                    },
                    exception=e,
                    severity="high"
                )
            except Exception as br_e:
                logger.warning(f"Could not create bug report: {br_e}")
            # Keep status as 'scheduled' so it can be retried
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notifications
                    SET status = 'scheduled', 
                        sent_at = NULL, 
                        sent_count = 0,
                        failed_count = 1,
                        error_message = $2,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    notification_id,
                    error_msg
                )
            return {"sent": 0, "failed": 1, "total": 1}
    
    # Handle 'user_group' type - send to users in selected groups
    user_ids_to_send: List[int] = []
    if recipient_type == 'user_group':
        if not recipient_ids:
            logger.warning(f"No group IDs specified for notification {notification_id}")
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notifications
                    SET status = 'cancelled', 
                        sent_at = NULL, 
                        sent_count = 0,
                        failed_count = 0,
                        error_message = 'No groups specified',
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    notification_id
                )
            return {"sent": 0, "failed": 0, "total": 0}
        
        # Get all users from selected groups, deduplicated
        # Apply same filtering rules: notifications_enabled, state = 'ACTIVE', finishedonboarding
        # Also filter out users without Telegram link and users with negative IDs (groups, not private chats)
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT u.user_id
                FROM users u
                INNER JOIN user_group_memberships ugm ON u.user_id = ugm.user_id
                WHERE ugm.group_id = ANY($1)
                  AND u.notifications_enabled = true
                  AND u.state = 'ACTIVE'
                  AND u.finishedonboarding = true
                  AND u.user_telegram_link IS NOT NULL
                  AND u.user_telegram_link != ''
                  AND u.user_id > 0
                """,
                recipient_ids
            )
            user_ids_to_send = [row['user_id'] for row in rows]
            
            # Get group names for logging
            group_rows = await conn.fetch(
                """
                SELECT id, name
                FROM user_groups
                WHERE id = ANY($1)
                """,
                recipient_ids
            )
            group_names = [row['name'] for row in group_rows]
            logger.info(f"Notification {notification_id} will be sent to {len(user_ids_to_send)} unique users from groups: {', '.join(group_names)}")
    
    # Handle 'all' and 'user' types - send to individual users
    if recipient_type in ['all', 'user']:
        async with db_pool.acquire() as conn:
            if recipient_type == 'all':
                # Get all active users with notifications enabled
                # Filter out users without Telegram link and users with negative IDs (groups, not private chats)
                rows = await conn.fetch(
                    """
                    SELECT user_id
                    FROM users
                    WHERE notifications_enabled = true
                      AND state = 'ACTIVE'
                      AND finishedonboarding = true
                      AND user_telegram_link IS NOT NULL
                      AND user_telegram_link != ''
                      AND user_id > 0
                    """
                )
                user_ids_to_send = [row['user_id'] for row in rows]
            elif recipient_type == 'user':
                # Filter out users with notifications disabled
                if not recipient_ids:
                    user_ids_to_send = []
                else:
                    rows = await conn.fetch(
                        """
                        SELECT user_id
                        FROM users
                        WHERE user_id = ANY($1)
                          AND notifications_enabled = true
                          AND state = 'ACTIVE'
                          AND finishedonboarding = true
                          AND user_telegram_link IS NOT NULL
                          AND user_telegram_link != ''
                          AND user_id > 0
                        """,
                        recipient_ids
                    )
                    user_ids_to_send = [row['user_id'] for row in rows]
                    # Log if some users were filtered out
                    if len(user_ids_to_send) < len(recipient_ids):
                        filtered_out = set(recipient_ids) - set(user_ids_to_send)
                        logger.info(f"Filtered out {len(filtered_out)} users with notifications disabled or inactive: {filtered_out}")
    
    if not user_ids_to_send:
        logger.warning(f"No recipients found in selected groups for notification {notification_id}")
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notifications
                SET status = 'cancelled', 
                    sent_at = NULL, 
                    sent_count = 0,
                    failed_count = 0,
                    error_message = 'No active users with notifications enabled in selected groups',
                    updated_at = NOW()
                WHERE id = $1
                """,
                notification_id
            )
        return {"sent": 0, "failed": 0, "total": 0}
        logger.warning(f"No recipients found for notification {notification_id}")
        # Mark as cancelled since there are no recipients to send to
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notifications
                SET status = 'cancelled', 
                    sent_at = NULL, 
                    sent_count = 0,
                    failed_count = 0,
                    error_message = 'No recipients found',
                    updated_at = NOW()
                WHERE id = $1
                """,
                notification_id
            )
        return {"sent": 0, "failed": 0, "total": 0}
    
    # Send notifications in batches to respect Telegram rate limits
    # Telegram allows up to 30 messages per second to different users
    # We'll send in batches of 25 with small delays to stay within limits
    # NOTE: We do NOT hold DB connection during sending to avoid connection pool exhaustion
    sent_count = 0
    failed_count = 0
    batch_size = 25  # Send 25 messages per batch
    delay_between_batches = 1.0  # 1 second delay between batches
    
    total_users = len(user_ids_to_send)
    logger.info(f"Starting to send notification to {total_users} users in batches of {batch_size}")
    
    # Split users into batches
    batch_num = 0
    for i in range(0, len(user_ids_to_send), batch_size):
        batch_num += 1
        batch = user_ids_to_send[i:i + batch_size]
        logger.info(f"Processing batch {batch_num}: {len(batch)} users (users {i+1}-{min(i+batch_size, total_users)} of {total_users})")
        
        # Send batch in parallel (up to batch_size concurrent sends)
        # NOTE: For user_group type, we continue sending even if some users fail (requirement #6)
        tasks = [
            send_notification_to_user(
                bot=bot,
                user_id=user_id,
                message_text=message_text,
                db_pool=db_pool,
                image_url=image_url
            )
            for user_id in batch
        ]
        
        # Wait for batch to complete with timeout
        # For small batches (1-5 users), use 5 seconds per user, for larger batches use 3 seconds per user
        # Reduced timeouts to prevent hanging
        timeout_per_user = 5.0 if len(batch) <= 5 else 3.0
        batch_timeout = timeout_per_user * len(batch)
        try:
            logger.debug(f"Batch {batch_num} timeout: {batch_timeout:.1f}s ({timeout_per_user:.1f}s per user)")
            # Use asyncio.wait_for directly on gather (gather already returns a coroutine)
            # For user_group type, use return_exceptions=True to continue on errors
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=batch_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Batch {batch_num} timed out after {batch_timeout:.1f} seconds ({timeout_per_user:.1f}s per user)")
            # Mark all remaining as failed, but continue processing other batches
            failed_count += len(batch)
            results = [False] * len(batch)
        
        # Count successes and failures
        # For user_group type, errors don't stop the process (requirement #6)
        for idx, result in enumerate(results):
            user_id = batch[idx]
            if isinstance(result, Exception):
                logger.error(f"Exception sending notification to user {user_id}: {result}")
                failed_count += 1
                # Continue processing - don't stop for user_group type
            elif result:
                sent_count += 1
            else:
                failed_count += 1
                # Continue processing - don't stop for user_group type
        
        logger.info(f"Batch {batch_num} completed: {sent_count} sent, {failed_count} failed so far")
        
        # Delay between batches to respect rate limits (except for last batch)
        if i + batch_size < len(user_ids_to_send):
            logger.debug(f"Waiting {delay_between_batches}s before next batch...")
            await asyncio.sleep(delay_between_batches)
    
    # Update notification status with statistics (re-acquire connection)
    async with db_pool.acquire() as conn:
        error_msg = None
        # Determine final status: only mark as 'sent' if at least one message was successfully sent
        if sent_count > 0:
            # At least one message was sent successfully
            final_status = 'sent'
            if failed_count > 0:
                # Partial failure
                error_msg = f"Failed to send to {failed_count} of {len(user_ids_to_send)} recipients"
        else:
            # All messages failed - check if this is a retry (failed_count already > 0)
            # If it's already failed before, mark as cancelled to prevent infinite retries
            # Otherwise, keep as scheduled for one retry attempt
            current_notification = await conn.fetchrow(
                "SELECT failed_count FROM notifications WHERE id = $1",
                notification_id
            )
            previous_failed_count = current_notification['failed_count'] if current_notification else 0
            
            # If already failed before or if this is a send-now notification that failed immediately,
            # mark as cancelled to prevent infinite retries
            if previous_failed_count > 0 or failed_count > 0:
                final_status = 'cancelled'
                error_msg = f"Failed to send to all {failed_count} recipients after retry attempts. Notification cancelled."
            else:
                # First failure - allow one retry
                final_status = 'scheduled'
                error_msg = f"Failed to send to all {failed_count} recipients. Will retry once more."
        
        await conn.execute(
            """
            UPDATE notifications
            SET status = $2, 
                sent_at = CASE WHEN $3 > 0 THEN NOW() ELSE sent_at END,
                sent_count = $3,
                failed_count = $4,
                error_message = $5,
                updated_at = NOW()
            WHERE id = $1
            """,
            notification_id,
            final_status,
            sent_count,
            failed_count,
            error_msg
        )
    
    logger.info(
        f"Notification {notification_id} sent: {sent_count} successful, "
        f"{failed_count} failed out of {len(user_ids_to_send)} total"
    )
    
    return {
        "sent": sent_count,
        "failed": failed_count,
        "total": len(user_ids_to_send)
    }


async def process_scheduled_notifications(
    bot: Bot,
    db_pool: asyncpg.Pool
) -> None:
    """
    Check for scheduled notifications that are due and send them
    
    This function should be called periodically by the scheduler
    """
    logger.info("Processing scheduled notifications")
    logger.debug(f"[DEBUG] process_scheduled_notifications called at {datetime.now()}")
    
    try:
        async with db_pool.acquire() as conn:
            # Find notifications that are scheduled and due
            now = datetime.now()
            logger.debug(f"[DEBUG] Checking for notifications scheduled before/at {now}")
            
            notifications = await conn.fetch(
                """
                SELECT id, scheduled_at, status, sent_count, failed_count
                FROM notifications
                WHERE (status = 'scheduled' AND (scheduled_at IS NULL OR scheduled_at <= $1))
                   OR (status = 'sent' AND sent_count = 0 AND failed_count = 0 AND scheduled_at IS NULL)
                ORDER BY scheduled_at ASC NULLS FIRST
                LIMIT 10
                """,
                now
            )
            
            logger.debug(f"[DEBUG] Found {len(notifications)} notifications to process")
            
            if not notifications:
                logger.debug("No scheduled notifications due")
                return
            
            logger.info(f"Found {len(notifications)} scheduled notifications to send")
            
            for notification in notifications:
                notification_id = notification['id']
                scheduled_at = notification['scheduled_at']
                
                logger.info(
                    f"Processing notification {notification_id} "
                    f"(scheduled: {scheduled_at})"
                )
                logger.debug(f"[DEBUG] Processing notification ID={notification_id}, scheduled_at={scheduled_at}")
                
                try:
                    result = await send_notification(
                        bot=bot,
                        notification_id=notification_id,
                        db_pool=db_pool
                    )
                    
                    logger.debug(f"[DEBUG] Notification {notification_id} result: {result}")
                    
                    if "error" in result:
                        logger.error(
                            f"Failed to send notification {notification_id}: {result['error']}"
                        )
                    else:
                        logger.info(
                            f"Notification {notification_id} sent: "
                            f"{result.get('sent', 0)} successful, "
                            f"{result.get('failed', 0)} failed"
                        )
                except Exception as e:
                    logger.error(
                        f"Error processing notification {notification_id}: {e}",
                        exc_info=True
                    )
                    
    except Exception as e:
        logger.error(f"Error in process_scheduled_notifications: {e}", exc_info=True)
