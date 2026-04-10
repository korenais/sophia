from __future__ import annotations

import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables early to ensure BOT_LANGUAGE is available
load_dotenv()


async def get_pool(db_url: str) -> asyncpg.pool.Pool:
    return await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=5)


# Users
async def get_user_state(pool: asyncpg.pool.Pool, user_id: int) -> Optional[str]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("select state from public.users where user_id=$1", user_id)
        return row["state"] if row else None


async def upsert_user_state(pool: asyncpg.pool.Pool, user_id: int, state: str, chat_id: Optional[int] = None) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into public.users(user_id, state, chat_id)
            values($1, $2, $3)
            on conflict (user_id) do update set state=excluded.state, chat_id=coalesce(excluded.chat_id, users.chat_id), updated_at=now()
            """,
            user_id,
            state,
            chat_id,
        )

async def set_user_language(pool: asyncpg.pool.Pool, user_id: int, language: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into public.users(user_id, language)
            values($1, $2)
            on conflict (user_id) do update set language=excluded.language, updated_at=now()
            """,
            user_id,
            language,
        )

async def get_user_language(pool: asyncpg.pool.Pool, user_id: int) -> str:
    """Get bot language from BOT_LANGUAGE environment variable, ignore user's DB language"""
    import os
    bot_language = os.getenv("BOT_LANGUAGE", "ru")
    return bot_language.lower() if bot_language else 'ru'


async def set_user_onboarding_data(
    pool: asyncpg.pool.Pool,
    user_id: int,
    onboarding: Dict[str, Optional[str]],
    vectors: Dict[str, Optional[List[float]]],
) -> None:
    # Convert birthday string to date object if present
    birthday_date = None
    if onboarding.get("birthday"):
        try:
            birthday_str = onboarding.get("birthday")
            birthday_date = datetime.strptime(birthday_str, "%Y-%m-%d").date()
        except ValueError as e:
            print(f"Error parsing birthday '{birthday_str}': {e}")
            birthday_date = None
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into public.users(
                user_id, intro_name, intro_location, intro_description, 
                intro_image, intro_linkedin, intro_hobbies_drivers, intro_skills, intro_birthday, field_of_activity,
                vector_description, vector_location, user_telegram_link,
                finishedonboarding, created_at, updated_at
              )
             values($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, true, now(), now())
            on conflict (user_id) do update set
              intro_name=excluded.intro_name,
              intro_location=excluded.intro_location,
              intro_description=excluded.intro_description,
              intro_image=excluded.intro_image,
              intro_linkedin=excluded.intro_linkedin,
              intro_hobbies_drivers=excluded.intro_hobbies_drivers,
              intro_skills=excluded.intro_skills,
              intro_birthday=excluded.intro_birthday,
              field_of_activity=excluded.field_of_activity,
              vector_description=excluded.vector_description,
              vector_location=excluded.vector_location,
              user_telegram_link=COALESCE(excluded.user_telegram_link, users.user_telegram_link),
              finishedonboarding=true,
              updated_at=now()
            """,
            user_id,
            onboarding.get("name"),
            onboarding.get("location"),
            onboarding.get("description"),
            onboarding.get("photoId"),
            onboarding.get("linkedin"),
            onboarding.get("hobbies_drivers"),
            onboarding.get("skills"),
            birthday_date,
            onboarding.get("field_of_activity"),
            vectors.get("descriptionVector"),
            vectors.get("locationVector"),
            onboarding.get("user_telegram_link"),
        )


async def get_user_info(pool: asyncpg.pool.Pool, user_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            select user_id, intro_description, intro_image, intro_name, intro_location, intro_linkedin, 
                   intro_hobbies_drivers, intro_skills, intro_birthday, field_of_activity, user_telegram_link,
                   notifications_enabled
            from public.users where user_id=$1
            """,
            user_id,
        )
        return dict(row) if row else None


async def get_matchable_users(pool: asyncpg.pool.Pool, exclude_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get users who are eligible for matching.
    
    Requirements:
    - finishedonboarding = true
    - state = 'ACTIVE'
    - vector_description is not null (for similarity calculation)
    - intro_description is not null AND length >= 10 (must have real description, not just default vector)
    - matches_disabled = false or NULL
    
    Note: Users without real descriptions are excluded from matching even if they have a default vector.
    This prevents matching empty profiles while still allowing them to use /my_matches command.
    
    Note: This function does NOT filter out users with recent meetings - that check is done in _generate_user_pairs()
    to allow more efficient querying. The exclusion of recent meetings is handled at the pair generation level.
    """
    async with pool.acquire() as conn:
        query = """
            select user_id, vector_description, vector_location
            from public.users
            where finishedonboarding = true 
            and state='ACTIVE' 
            and vector_description is not null
            and intro_description is not null
            and length(trim(intro_description)) >= 10
            and (matches_disabled IS NULL OR matches_disabled = false)
        """
        params = []
        
        if exclude_user_id:
            query += " and user_id != $1"
            params.append(exclude_user_id)
        
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


# Meetings
async def create_meetings(pool: asyncpg.pool.Pool, pairs: List[tuple[int, int]]) -> List[str]:
    """Create meeting records for user pairs and return meeting IDs"""
    meeting_ids = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            for u1, u2 in pairs:
                meeting_id = await conn.fetchval(
                    """
                    insert into public.meetings(user_1_id, user_2_id, status, created_at, last_updated)
                    values($1, $2, 'new', now(), now())
                    returning id
                    """,
                    u1,
                    u2,
                )
                meeting_ids.append(str(meeting_id))
    return meeting_ids

async def get_new_meetings(pool: asyncpg.pool.Pool) -> List[Dict[str, Any]]:
    """Get all new meetings that need notification"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_1_id, user_2_id, status, created_at, last_updated
            FROM public.meetings
            WHERE status = 'new'
            ORDER BY created_at ASC
            """
        )
        return [dict(row) for row in rows]

async def update_meeting_status(pool: asyncpg.pool.Pool, meeting_id: str, status: str) -> None:
    """Update meeting status"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE public.meetings
            SET status = $2, last_updated = NOW()
            WHERE id = $1
            """,
            int(meeting_id), status
        )

async def get_meeting_by_id(pool: asyncpg.pool.Pool, meeting_id: str) -> Optional[Dict[str, Any]]:
    """Get meeting by ID"""
    async with pool.acquire() as conn:
        # Check which columns exist
        columns_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'meetings' AND table_schema = 'public'
        """
        available_columns = await conn.fetch(columns_query)
        column_names = [row['column_name'] for row in available_columns]
        
        # Build SELECT query with only existing columns
        base_columns = ['id', 'user_1_id', 'user_2_id', 'status', 'created_at', 'last_updated']
        select_columns = [col for col in base_columns if col in column_names]
        
        # Add optional columns if they exist
        if 'call_successful' in column_names:
            select_columns.append('call_successful')
        if 'sent_followup_message' in column_names:
            select_columns.append('sent_followup_message')
        
        row = await conn.fetchrow(
            f"""
            SELECT {', '.join(select_columns)}
            FROM public.meetings
            WHERE id = $1
            """,
            int(meeting_id)
        )
        return dict(row) if row else None

async def update_meeting_followup_status(pool: asyncpg.pool.Pool, meeting_id: str, sent_followup: bool) -> None:
    """Update meeting followup status"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE public.meetings
            SET sent_followup_message = $2, last_updated = NOW()
            WHERE id = $1
            """,
            meeting_id, sent_followup
        )


# Feedbacks
async def insert_feedback(pool: asyncpg.pool.Pool, user_id: int, fb_type: str, text: str) -> None:
    import logging
    logger = logging.getLogger(__name__)
    
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                insert into public.feedbacks(user_id, type, text)
                values($1, $2, $3)
                """,
                user_id,
                fb_type,
                text,
            )
            logger.info(f"Feedback inserted successfully: user_id={user_id}, type={fb_type}")
        except Exception as e:
            logger.error(f"Error inserting feedback: user_id={user_id}, type={fb_type}, error={e}", exc_info=True)
            raise


# Match blocks
async def block_user(pool: asyncpg.pool.Pool, user_id: int, blocked_user_id: int) -> None:
    """Block a specific user from being matched"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.match_blocks(user_id, blocked_user_id, created_at)
            VALUES($1, $2, now())
            ON CONFLICT (user_id, blocked_user_id) DO NOTHING
            """,
            user_id,
            blocked_user_id,
        )

async def disable_all_matches(pool: asyncpg.pool.Pool, user_id: int) -> None:
    """Disable all matches for a user"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE public.users
            SET matches_disabled = true, updated_at = now()
            WHERE user_id = $1
            """,
            user_id,
        )

async def enable_all_matches(pool: asyncpg.pool.Pool, user_id: int) -> None:
    """Enable all matches for a user"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE public.users
            SET matches_disabled = false, updated_at = now()
            WHERE user_id = $1
            """,
            user_id,
        )

async def is_user_blocked(pool: asyncpg.pool.Pool, user_id: int, other_user_id: int) -> bool:
    """Check if a user has blocked another user"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM public.match_blocks
            WHERE user_id = $1 AND blocked_user_id = $2
            """,
            user_id,
            other_user_id,
        )
        return row is not None

async def get_meeting_by_users(pool: asyncpg.pool.Pool, user1_id: int, user2_id: int) -> Optional[Dict[str, Any]]:
    """Get meeting by user pair"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_1_id, user_2_id, status, created_at, last_updated
            FROM public.meetings
            WHERE (user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user1_id,
            user2_id,
        )
        return dict(row) if row else None


async def has_recent_meeting(pool: asyncpg.pool.Pool, user1_id: int, user2_id: int, months: int = 6) -> bool:
    """
    Check if users had a completed meeting (status = 'met') within the specified number of months.
    Returns True if there was a meeting with status 'met' within the last N months.
    
    Uses last_updated timestamp which is updated when meeting status changes to 'met'.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 
            FROM public.meetings
            WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
              AND status = 'met'
              AND last_updated >= NOW() - (INTERVAL '1 month' * $3)
            ORDER BY last_updated DESC
            LIMIT 1
            """,
            user1_id,
            user2_id,
            months
        )
        return row is not None


