import os
import asyncpg
import httpx
import math
from fastapi import FastAPI, HTTPException, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Any
import re

DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@db:5432/postgres")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEV_TMA_BYPASS = os.getenv("DEV_TMA_BYPASS", "").lower() in {"1", "true", "yes"}
DEV_TMA_USER_ID = int(os.getenv("DEV_TMA_USER_ID", "999000001"))
TMA_ALLOWED_USER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("TMA_ALLOWED_USER_IDS", "").split(",")
    if user_id.strip().isdigit()
}

app = FastAPI(title="Sophia API")

# Get allowed origins from environment variable
# Format: comma-separated list, e.g., "https://vm18.digisoov.ee,http://localhost:8081"
# Note: When allow_credentials=True, you CANNOT use allow_origins=["*"]
# You must specify explicit origins
allowed_origins_env = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "https://vm18.digisoov.ee,http://localhost:8081,http://localhost:5173"
)
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: asyncpg.pool.Pool | None = None


async def _ensure_dev_tma_user() -> None:
    """Create a lightweight local TMA user when dev bypass is enabled."""
    if not DEV_TMA_BYPASS or pool is None:
        return

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.users (
                user_id,
                chat_id,
                username,
                intro_name,
                intro_location,
                intro_description,
                intro_linkedin,
                intro_hobbies_drivers,
                intro_skills,
                field_of_activity,
                user_telegram_link,
                state,
                finishedonboarding,
                notifications_enabled,
                matches_disabled,
                created_at,
                updated_at
            ) VALUES (
                $1,
                $1,
                'dev_tma_user',
                'Local TMA User',
                'Tallinn, Estonia',
                'Local development profile for Telegram Mini App testing.',
                'https://linkedin.com/in/local-tma-user',
                'Building, testing, shipping',
                'Product, Engineering, Community',
                'Local Development',
                'https://t.me/example',
                'ACTIVE',
                true,
                true,
                false,
                now(),
                now()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                intro_name = EXCLUDED.intro_name,
                intro_location = EXCLUDED.intro_location,
                intro_description = EXCLUDED.intro_description,
                intro_linkedin = EXCLUDED.intro_linkedin,
                intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
                intro_skills = EXCLUDED.intro_skills,
                field_of_activity = EXCLUDED.field_of_activity,
                user_telegram_link = EXCLUDED.user_telegram_link,
                state = EXCLUDED.state,
                finishedonboarding = EXCLUDED.finishedonboarding,
                notifications_enabled = EXCLUDED.notifications_enabled,
                matches_disabled = EXCLUDED.matches_disabled,
                updated_at = now()
            """,
            DEV_TMA_USER_ID,
        )


def is_base64_image(data: str) -> bool:
    """Check if the data is a base64 encoded image"""
    if not data:
        return False
    try:
        import base64
        # Check if it's valid base64
        base64.b64decode(data, validate=True)
        # Check if it starts with common image headers
        decoded = base64.b64decode(data)
        return decoded.startswith(b'\xff\xd8\xff') or decoded.startswith(b'\x89PNG') or decoded.startswith(b'GIF')
    except:
        return False

def get_data_url_from_base64(base64_data: str) -> str | None:
    """Convert base64 image data to data URL"""
    if not is_base64_image(base64_data):
        return None
    
    # Try to detect image format
    try:
        import base64
        decoded = base64.b64decode(base64_data)
        if decoded.startswith(b'\xff\xd8\xff'):
            return f"data:image/jpeg;base64,{base64_data}"
        elif decoded.startswith(b'\x89PNG'):
            return f"data:image/png;base64,{base64_data}"
        elif decoded.startswith(b'GIF'):
            return f"data:image/gif;base64,{base64_data}"
        else:
            return f"data:image/jpeg;base64,{base64_data}"  # Default to JPEG
    except:
        return None


def get_telegram_image_url(file_id: str) -> str | None:
    """Convert Telegram file ID to direct image URL"""
    if not file_id or not TELEGRAM_TOKEN:
        return None
    
    try:
        # Get file info from Telegram
        file_info_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        response = httpx.get(file_info_url)
        response.raise_for_status()
        
        file_info = response.json()
        if file_info.get("ok") and file_info.get("result", {}).get("file_path"):
            file_path = file_info["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        
        return None
    except Exception as e:
        print(f"Error getting Telegram image URL: {e}")
        return None


def process_user_data(user_dict: dict) -> dict:
    """Process user data for API response - convert dates and images"""
    # Convert date to string for JSON response (handle None values)
    if user_dict.get("intro_birthday") is not None:
        user_dict["intro_birthday"] = str(user_dict["intro_birthday"])
    else:
        user_dict["intro_birthday"] = None
    
    # Normalize matches_disabled: null or false means enabled (false), only true means disabled
    # Ensure we preserve True values and only normalize None to False
    matches_disabled_value = user_dict.get("matches_disabled")
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"process_user_data: matches_disabled raw = {matches_disabled_value}, type = {type(matches_disabled_value)}")
    
    if matches_disabled_value is None:
        user_dict["matches_disabled"] = False
        logger.debug(f"process_user_data: normalized None to False")
    # Explicitly ensure boolean type (in case of any type conversion issues)
    elif isinstance(matches_disabled_value, bool):
        user_dict["matches_disabled"] = matches_disabled_value
        logger.debug(f"process_user_data: preserved boolean value = {matches_disabled_value}")
    else:
        # Convert truthy/falsy to boolean
        user_dict["matches_disabled"] = bool(matches_disabled_value)
        logger.debug(f"process_user_data: converted to boolean = {user_dict['matches_disabled']}")
    
    logger.debug(f"process_user_data: final matches_disabled = {user_dict.get('matches_disabled')}")

    # Normalize finishedonboarding: preserve boolean values, normalize None to True (default)
    # Database uses lowercase 'finishedonboarding'
    finished_onboarding_value = None
    if "finishedonboarding" in user_dict:
        finished_onboarding_value = user_dict["finishedonboarding"]
    
    # Set normalized value
    if finished_onboarding_value is None:
        user_dict["finishedonboarding"] = True
    elif isinstance(finished_onboarding_value, bool):
        user_dict["finishedonboarding"] = finished_onboarding_value
    else:
        user_dict["finishedonboarding"] = bool(finished_onboarding_value)

    # Process image
    if user_dict.get("intro_image"):
        if is_base64_image(user_dict["intro_image"]):
            user_dict["intro_image"] = get_data_url_from_base64(user_dict["intro_image"])
        elif not user_dict["intro_image"].startswith(("http://", "https://", "data:")):
            # Convert Telegram file ID to URL
            user_dict["intro_image"] = get_telegram_image_url(user_dict["intro_image"])
    
    return user_dict


class User(BaseModel):
    user_id: int
    intro_name: str | None = None
    intro_location: str | None = None
    intro_description: str | None = None
    intro_linkedin: str | None = None
    intro_hobbies_drivers: str | None = None
    intro_skills: str | None = None
    field_of_activity: str | None = None
    intro_birthday: date | None = None
    intro_image: str | None = None
    user_telegram_link: str | None = None
    state: str | None = None
    notifications_enabled: bool | None = True
    matches_disabled: bool | None = False
    finishedonboarding: bool | None = True


async def _save_configuration_bug_report(
    pool: asyncpg.pool.Pool,
    error_type: str,
    error_message: str,
    context: dict
) -> None:
    """Save configuration bug report to feedbacks table"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Format bug report content
        report_content = f"""Configuration Issue Detected

Type: {error_type}
Message: {error_message}

Context:
{chr(10).join(f"  {k}: {v}" for k, v in context.items())}

This is an automatic configuration validation report.
Please review and update your environment configuration.
"""
        
        # Check for duplicate reports in last 24 hours
        async with pool.acquire() as conn:
            # Check if similar report exists in last 24 hours
            existing = await conn.fetchrow(
                """
                SELECT id FROM public.feedbacks
                WHERE user_id = 0
                  AND type = 'issue'
                  AND text LIKE $1
                  AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                f"%{error_type}%"
            )
            
            if existing:
                logger.info(f"Configuration issue already reported recently (ID: {existing['id']}), skipping duplicate")
                return
            
            # Insert bug report (user_id=0 indicates system-generated)
            await conn.execute(
                """
                INSERT INTO public.feedbacks(user_id, type, text)
                VALUES(0, 'issue', $1)
                """,
                report_content
            )
            logger.warning(f"Configuration bug report created: {error_type}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to save configuration bug report: {e}", exc_info=True)


async def _validate_configuration(pool: asyncpg.pool.Pool) -> None:
    """Validate configuration and report issues"""
    import logging
    logger = logging.getLogger(__name__)
    
    issues_found = []
    
    # Get current configuration values
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
    vite_api_base_url = os.getenv("VITE_API_BASE_URL", "")
    
    # Check if CORS_ALLOWED_ORIGINS is explicitly set
    # Default includes production domain which may not be correct
    default_cors_origins = "https://vm18.digisoov.ee,http://localhost:8081,http://localhost:5173"
    if not cors_origins_env:
        issues_found.append({
            "type": "CORS Configuration Missing",
            "message": "CORS_ALLOWED_ORIGINS environment variable is not set. Using default value which may not match your deployment.",
            "context": {
                "default_value": default_cors_origins,
                "recommendation": "Set CORS_ALLOWED_ORIGINS environment variable to explicitly list allowed origins for your deployment"
            }
        })
    
    # Check if VITE_API_BASE_URL uses localhost when server is not localhost
    is_localhost_config = (
        vite_api_base_url.startswith("http://localhost") or 
        vite_api_base_url.startswith("http://127.0.0.1")
    )
    
    # Detect if we're likely in production environment
    # Indicators: non-localhost origins in CORS, or production-like domain in default
    is_production = False
    non_localhost_origins = []
    
    if cors_origins_env:
        origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        non_localhost_origins = [
            o for o in origins 
            if not (o.startswith("http://localhost") or 
                   o.startswith("http://127.0.0.1") or
                   o.startswith("https://localhost"))
        ]
        # If we have any non-localhost origins (excluding localhost variants), we're likely in production
        if non_localhost_origins:
            is_production = True
    else:
        # Using default - check if default contains production domain
        if "vm18.digisoov.ee" in default_cors_origins or any(
            origin.startswith("https://") and "localhost" not in origin.lower()
            for origin in default_cors_origins.split(",")
        ):
            # Default contains production domain - likely production
            is_production = True
    
    # Additional check: if VITE_API_BASE_URL contains production domain but CORS doesn't include it
    if vite_api_base_url and not is_localhost_config:
        # Extract domain from VITE_API_BASE_URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(vite_api_base_url)
            api_domain = f"{parsed.scheme}://{parsed.netloc}"
            # If API URL has a domain but CORS doesn't include localhost equivalents, check mismatch
            if cors_origins_env:
                origins_list = [o.strip() for o in cors_origins_env.split(",")]
                # Check if the frontend origin (without port or with common frontend port) is in CORS
                # Frontend typically uses same domain but different port or no port
                frontend_base = f"{parsed.scheme}://{parsed.hostname}"
                if not any(
                    frontend_base in origin or origin.startswith(frontend_base)
                    for origin in origins_list
                ):
                    # CORS doesn't include the API domain's base - potential mismatch
                    pass  # Could add warning here if needed
        except Exception:
            pass  # Skip if URL parsing fails
    
    # Report localhost config in production
    if is_production and is_localhost_config:
        issues_found.append({
            "type": "Localhost Configuration in Production",
            "message": f"VITE_API_BASE_URL is set to localhost ({vite_api_base_url}) but server appears to be in production environment with non-localhost origins.",
            "context": {
                "vite_api_base_url": vite_api_base_url,
                "cors_origins": cors_origins_env or f"default ({default_cors_origins})",
                "non_localhost_origins": ", ".join(non_localhost_origins) if non_localhost_origins else "none",
                "recommendation": "Update VITE_API_BASE_URL to use your production domain instead of localhost"
            }
        })
    
    # Report all issues found
    for issue in issues_found:
        await _save_configuration_bug_report(
            pool,
            issue["type"],
            issue["message"],
            issue["context"]
        )
        logger.error(f"Configuration issue detected: {issue['type']} - {issue['message']}")


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=5)
    
    # Validate configuration and report issues
    await _validate_configuration(pool)
    await _ensure_dev_tma_user()


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint for deployment scripts and monitoring"""
    try:
        # Check database connection
        if pool is None:
            raise HTTPException(status_code=503, detail="Database pool not initialized")
        
        async with pool.acquire() as conn:
            # Simple query to verify database connection
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "pool_size": pool.get_size() if pool else 0,
            "pool_free": pool.get_idle_size() if pool else 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")


@app.get("/api/users", response_model=list[User])
async def get_users():
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select user_id, intro_name, intro_location, intro_description, intro_linkedin, 
                   intro_hobbies_drivers, intro_skills, field_of_activity, intro_birthday, intro_image, user_telegram_link, state, notifications_enabled, matches_disabled, finishedonboarding
            from public.users
            order by updated_at desc
            limit 100
            """
        )
        
        # Process user data for API response
        users = []
        for row in rows:
            user_data = process_user_data(dict(row))
            users.append(user_data)
        
        return users


@app.get("/api/meetings")
async def get_meetings():
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select m.id, m.user_1_id, u1.intro_name as user1_name,
                   m.user_2_id, u2.intro_name as user2_name,
                   m.status, m.created_at
            from public.meetings m
            join public.users u1 on u1.user_id = m.user_1_id
            join public.users u2 on u2.user_id = m.user_2_id
            order by m.created_at desc
            limit 100
            """
        )
        return [dict(r) for r in rows]


# User Management Endpoints
class UserCreate(BaseModel):
    user_id: int | None = None  # Made optional for auto-population
    chat_id: int | None = None  # Added for auto-population
    intro_name: str
    intro_location: str | None = None
    intro_description: str | None = None
    intro_linkedin: str | None = None
    intro_hobbies_drivers: str | None = None
    intro_skills: str | None = None
    field_of_activity: str | None = None
    intro_birthday: date | None = None
    intro_image: str | None = None
    user_telegram_link: str | None = None
    state: str | None = "ACTIVE"
    finishedonboarding: bool = True


class UserUpdate(BaseModel):
    intro_name: str | None = None
    intro_location: str | None = None
    intro_description: str | None = None
    intro_linkedin: str | None = None
    intro_hobbies_drivers: str | None = None
    intro_skills: str | None = None
    field_of_activity: str | None = None
    intro_birthday: date | None = None
    intro_image: str | None = None
    user_telegram_link: str | None = None
    state: str | None = None
    finishedonboarding: bool | None = None
    notifications_enabled: bool | None = None
    matches_disabled: bool | None = None


class TelegramValidationRequest(BaseModel):
    username: str


class TelegramValidationResponse(BaseModel):
    user_id: int | None = None
    chat_id: int | None = None
    username: str | None = None
    normalized_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_valid: bool
    message: str


class LinkedInValidationRequest(BaseModel):
    url: str


class LinkedInValidationResponse(BaseModel):
    is_valid: bool
    message: str
    profile_data: dict | None = None


@app.post("/api/users", response_model=User)
async def create_user(user_data: UserCreate):
    """Create a new user"""
    # Validate user_telegram_link format: must be either valid username or numeric user_id
    if user_data.user_telegram_link:
        telegram_link = user_data.user_telegram_link.strip()
        # Check if it's a numeric user_id
        is_numeric_id = telegram_link.isdigit()
        # Check if it's a valid Telegram username (5-32 chars, alphanumeric + underscore)
        is_valid_username = bool(re.match(r'^[a-zA-Z0-9_]{5,32}$', telegram_link))
        
        if not is_numeric_id and not is_valid_username:
            raise HTTPException(
                status_code=400, 
                detail="user_telegram_link must be a valid Telegram username (5-32 chars, alphanumeric + underscore) or numeric User ID"
            )
    
    assert pool is not None
    async with pool.acquire() as conn:
        # Determine user_id and chat_id
        user_id = user_data.user_id
        chat_id = user_data.chat_id
        
        # If user_id is not provided, we need to generate one or get it from Telegram validation
        if user_id is None:
            if user_data.user_telegram_link:
                # Try to get user_id from existing Telegram username in database
                existing_user = await conn.fetchrow(
                    "SELECT user_id FROM users WHERE user_telegram_link = $1",
                    user_data.user_telegram_link
                )
                if existing_user:
                    user_id = existing_user['user_id']
                    chat_id = user_id  # chat_id is typically same as user_id for private chats
                else:
                    # Generate a temporary user_id (this should be replaced when user interacts with bot)
                    # For now, we'll use a negative number to indicate it's temporary
                    import random
                    user_id = -random.randint(100000, 999999)
                    chat_id = user_id
            else:
                raise HTTPException(status_code=400, detail="Either user_id or user_telegram_link must be provided")
        
        # Set chat_id if not provided
        if chat_id is None:
            chat_id = user_id
        
        # Check if user already exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # For admin-created users, default finishedonboarding to true if not explicitly set
        # This ensures they can receive birthday notifications and other features
        finished_onboarding = user_data.finishedonboarding
        if finished_onboarding is None:
            finished_onboarding = True  # Default to true for admin-created users
        
        # Create vector_description if description is provided, otherwise create default vector
        # This ensures users can use /my_matches even if they don't have a description yet
        vector_description = None
        if user_data.intro_description and len(user_data.intro_description.strip()) >= 10:
            # Try to vectorize the description if it's provided and long enough
            try:
                import sys
                import os
                # Add bot service path for imports
                bot_path = os.path.join(os.path.dirname(__file__), '..', 'bot')
                if bot_path not in sys.path:
                    sys.path.insert(0, bot_path)
                from vectorization import vectorize_description
                vector_description = await vectorize_description(user_data.intro_description)
            except Exception as e:
                print(f"Warning: Failed to vectorize description for user {user_id}: {e}")
        
        # If no vector was created (no description or vectorization failed), create default vector
        if vector_description is None:
            try:
                import sys
                import os
                bot_path = os.path.join(os.path.dirname(__file__), '..', 'bot')
                if bot_path not in sys.path:
                    sys.path.insert(0, bot_path)
                from vectorization import create_default_vector
                vector_description = await create_default_vector()
                print(f"Created default vector for user {user_id}")
            except Exception as e:
                print(f"Warning: Failed to create default vector for user {user_id}: {e}")
                # Fallback: use zero vector (3072 dimensions for text-embedding-3-large)
                vector_description = [0.0] * 3072
        
        # Insert new user
        await conn.execute(
            """
            INSERT INTO users (
                user_id, chat_id, intro_name, intro_location, intro_description, 
                intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity, intro_birthday,
                intro_image, user_telegram_link, state, finishedonboarding, vector_description, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW(), NOW())
            """,
            user_id,
            chat_id,
            user_data.intro_name,
            user_data.intro_location,
            user_data.intro_description,
            user_data.intro_linkedin,
            user_data.intro_hobbies_drivers,
            user_data.intro_skills,
            user_data.field_of_activity,
            user_data.intro_birthday,
            user_data.intro_image,
            user_data.user_telegram_link,
            user_data.state or "ACTIVE",  # Default to ACTIVE if not specified
            finished_onboarding,
            vector_description
        )
        
        # If birthday was set and it's today, reset last_birthday_greeting_sent to allow immediate sending
        if user_data.intro_birthday:
            from datetime import date
            today = date.today()
            birthday_date = user_data.intro_birthday
            if isinstance(birthday_date, str):
                from datetime import datetime
                birthday_date = datetime.strptime(birthday_date, "%Y-%m-%d").date()
            
            if birthday_date.month == today.month and birthday_date.day == today.day:
                # Birthday is today - reset last_birthday_greeting_sent to allow immediate sending
                await conn.execute(
                    "UPDATE users SET last_birthday_greeting_sent = NULL WHERE user_id = $1",
                    user_id
                )
        
        # Return the created user
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, intro_location, intro_description, intro_linkedin, 
                   intro_hobbies_drivers, intro_skills, intro_birthday, intro_image, user_telegram_link, state, notifications_enabled, matches_disabled, finishedonboarding
            FROM users WHERE user_id = $1
            """,
            user_id
        )
        
        return process_user_data(dict(row))


@app.put("/api/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate):
    """Update an existing user"""
    # Validate user_telegram_link format: must be either valid username or numeric user_id
    if user_data.user_telegram_link is not None:
        telegram_link = user_data.user_telegram_link.strip()
        # Check if it's a numeric user_id
        is_numeric_id = telegram_link.isdigit()
        # Check if it's a valid Telegram username (5-32 chars, alphanumeric + underscore)
        is_valid_username = bool(re.match(r'^[a-zA-Z0-9_]{5,32}$', telegram_link))
        
        if not is_numeric_id and not is_valid_username:
            raise HTTPException(
                status_code=400, 
                detail="user_telegram_link must be a valid Telegram username (5-32 chars, alphanumeric + underscore) or numeric User ID"
            )
    
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        # Map Python field names to database column names (PostgreSQL converts to lowercase unless quoted)
        field_mapping = {
            'finishedonboarding': 'finishedonboarding',  # Map API field to database column (both lowercase)
        }
        
        for field, value in user_data.dict(exclude_unset=True).items():
            # Include field if it's explicitly set (including None for clearing fields)
            # Use mapped field name if exists, otherwise use original field name
            db_field = field_mapping.get(field, field)
            update_fields.append(f"{db_field} = ${param_count}")
            values.append(value)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated_at
        update_fields.append("updated_at = NOW()")
        
        # Add user_id for WHERE clause
        values.append(user_id)
        
        query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE user_id = ${param_count}
        """
        
        await conn.execute(query, *values)
        
        # If birthday was updated, check if it's today and trigger immediate birthday check
        # Reset last_birthday_greeting_sent so that greeting can be sent immediately
        birthday_updated = 'intro_birthday' in user_data.dict(exclude_unset=True)
        if birthday_updated:
            from datetime import date
            birthday_value = user_data.dict(exclude_unset=True).get('intro_birthday')
            if birthday_value:
                try:
                    # Check if birthday is today
                    if isinstance(birthday_value, str):
                        from datetime import datetime
                        birthday_date = datetime.strptime(birthday_value, "%Y-%m-%d").date()
                    elif isinstance(birthday_value, date):
                        birthday_date = birthday_value
                    else:
                        birthday_date = None
                    
                    today = date.today()
                    if birthday_date and birthday_date.month == today.month and birthday_date.day == today.day:
                        # Birthday is today - reset last_birthday_greeting_sent to allow immediate sending
                        # This allows the bot's immediate check (check_birthday_for_user with force_send=True)
                        # to send greeting even if one was already sent today
                        await conn.execute(
                            "UPDATE users SET last_birthday_greeting_sent = NULL WHERE user_id = $1",
                            user_id
                        )
                        # Note: The bot's check_birthday_for_user (called from scenes.py) 
                        # uses force_send=True for bot updates. For API updates, we reset the flag
                        # so the next scheduled check (or immediate bot check if triggered) can send.
                except Exception as e:
                    # Ignore errors in birthday check - scheduler will handle it
                    pass
            else:
                # Birthday was cleared/set to None - reset tracking
                await conn.execute(
                    "UPDATE users SET last_birthday_greeting_sent = NULL WHERE user_id = $1",
                    user_id
                )
        
        # Update vector_description ONLY if intro_description was changed AND is meaningful (>=10 chars)
        # This ensures:
        # 1. When user adds real description, vector is updated for better matching
        # 2. Empty profiles are not matched (get_matchable_users requires intro_description >= 10)
        # 3. Users without descriptions keep existing/default vector so /my_matches still works
        if user_data.intro_description is not None:
            if user_data.intro_description and len(user_data.intro_description.strip()) >= 10:
                # Description is meaningful - vectorize it
                try:
                    import sys
                    import os
                    bot_path = os.path.join(os.path.dirname(__file__), '..', 'bot')
                    if bot_path not in sys.path:
                        sys.path.insert(0, bot_path)
                    from vectorization import vectorize_description
                    
                    description_text = user_data.intro_description.strip()
                    print(f"Attempting to vectorize description for user {user_id}, length: {len(description_text)}")
                    vector_description = await vectorize_description(description_text)
                    
                    if vector_description and len(vector_description) > 0:
                        await conn.execute(
                            "UPDATE users SET vector_description = $1, updated_at = NOW() WHERE user_id = $2",
                            vector_description, user_id
                        )
                        print(f"✓ Successfully updated vector_description for user {user_id} with real description vector (dimension: {len(vector_description)})")
                    else:
                        print(f"❌ ERROR: Failed to vectorize updated description for user {user_id} - vector_description is None or empty")
                        # Try to create default vector as fallback
                        try:
                            from vectorization import create_default_vector
                            default_vector = await create_default_vector()
                            if default_vector:
                                await conn.execute(
                                    "UPDATE users SET vector_description = $1, updated_at = NOW() WHERE user_id = $2",
                                    default_vector, user_id
                                )
                                print(f"Created default vector as fallback for user {user_id}")
                        except Exception as fallback_error:
                            print(f"❌ ERROR: Failed to create default vector fallback for user {user_id}: {fallback_error}")
                except Exception as e:
                    print(f"❌ ERROR: Failed to vectorize updated description for user {user_id}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # Description was cleared or is too short (< 10 chars)
                # Don't update vector - user will keep existing vector but won't be matched
                # (get_matchable_users requires intro_description >= 10)
                # Check if user has any vector at all - if not, create default for /my_matches
                existing_vector = await conn.fetchval(
                    "SELECT vector_description FROM users WHERE user_id = $1",
                    user_id
                )
                
                if existing_vector is None:
                    # User has no vector - create default so /my_matches works
                    try:
                        import sys
                        import os
                        bot_path = os.path.join(os.path.dirname(__file__), '..', 'bot')
                        if bot_path not in sys.path:
                            sys.path.insert(0, bot_path)
                        from vectorization import create_default_vector
                        vector_description = await create_default_vector()
                        if vector_description:
                            await conn.execute(
                                "UPDATE users SET vector_description = $1, updated_at = NOW() WHERE user_id = $2",
                                vector_description, user_id
                            )
                            print(f"Created default vector for user {user_id} (description too short/empty)")
                    except Exception as e:
                        print(f"Warning: Failed to create default vector for user {user_id}: {e}")
                else:
                    # Keep existing vector - user just won't be matched until they add description
                    print(f"User {user_id} description cleared/short - keeping existing vector, user won't be matched")
        
        # Return the updated user
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, intro_location, intro_description, intro_linkedin, 
                   intro_hobbies_drivers, intro_skills, intro_birthday, intro_image, user_telegram_link, state, notifications_enabled, matches_disabled, finishedonboarding
            FROM users WHERE user_id = $1
            """,
            user_id
        )
        
        return process_user_data(dict(row))


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    """Delete a user"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete related data first (foreign key constraints)
        # Delete thanks records where this user was the sender
        await conn.execute("DELETE FROM thanks WHERE sender_user_id = $1", user_id)
        
        await conn.execute("DELETE FROM meetings WHERE user_1_id = $1 OR user_2_id = $1", user_id)
        # NOTE: We preserve feedbacks even after user deletion for historical tracking
        # The frontend can handle displaying feedbacks from deleted users
        
        # Delete the user
        await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
        
        return {"message": "User deleted successfully"}


@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user by ID"""
    assert pool is not None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, intro_name, intro_location, intro_description, intro_linkedin, 
                   intro_hobbies_drivers, intro_skills, intro_birthday, intro_image, user_telegram_link, state, notifications_enabled, matches_disabled, finishedonboarding
            FROM users WHERE user_id = $1
            """,
            user_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert row to dict and process
        row_dict = dict(row)
        processed_data = process_user_data(row_dict)
        
        # Debug: log what we're returning
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"get_user {user_id}: matches_disabled after process = {processed_data.get('matches_disabled')}, type = {type(processed_data.get('matches_disabled'))}")
        
        # Create User model instance explicitly to ensure all fields are included
        user_model = User(**processed_data)
        logger.info(f"get_user {user_id}: User model matches_disabled = {user_model.matches_disabled}")
        
        return user_model


@app.get("/api/feedback")
async def get_feedback():
    """Get all feedback records, ordered by creation date (newest first)"""
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select id, user_id, text as message, 
                   CASE 
                     WHEN type = 'issue' THEN 'report'
                     WHEN type = 'feature' THEN 'suggestion'
                     ELSE type
                   END as type, 
                   created_at
            from public.feedbacks
            order by created_at desc
            """
        )
        return [dict(r) for r in rows]


@app.delete("/api/feedback/{feedback_id}")
async def delete_feedback(feedback_id: int):
    """Delete a specific feedback by ID"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if feedback exists
        existing = await conn.fetchrow(
            "SELECT id FROM feedbacks WHERE id = $1",
            feedback_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Delete the feedback
        await conn.execute("DELETE FROM feedbacks WHERE id = $1", feedback_id)
        
        return {"message": "Feedback deleted successfully"}


@app.delete("/api/feedback")
async def delete_all_feedback():
    """Delete all feedback records"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Get count before deletion
        count = await conn.fetchval("SELECT COUNT(*) FROM feedbacks")
        
        # Delete all feedback
        await conn.execute("DELETE FROM feedbacks")
        
        return {"message": f"All {count} feedback records deleted successfully"}


@app.delete("/api/feedback/type/{feedback_type}")
async def delete_feedback_by_type(feedback_type: str):
    """Delete all feedback of a specific type (report/suggestion)"""
    assert pool is not None
    
    # Convert frontend types back to database types
    db_type = 'issue' if feedback_type == 'report' else 'feature'
    
    async with pool.acquire() as conn:
        # Get count before deletion
        count = await conn.fetchval("SELECT COUNT(*) FROM feedbacks WHERE type = $1", db_type)
        
        # Delete feedback of specific type
        await conn.execute("DELETE FROM feedbacks WHERE type = $1", db_type)
        
        return {"message": f"All {count} {feedback_type} records deleted successfully"}


@app.get("/api/thanks/stats")
async def get_thanks_stats():
    """Get thanks statistics"""
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select receiver_username, count(*) as total
            from public.thanks
            group by receiver_username
            order by total desc, receiver_username asc
            """
        )
        return [dict(r) for r in rows]


@app.get("/api/thanks/top")
async def get_top_thanks(limit: int = 10):
    """Get top N users by thanks count"""
    assert pool is not None
    limit = max(1, min(limit, 50))  # Limit between 1 and 50
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select receiver_username, count(*) as total
            from public.thanks
            group by receiver_username
            order by total desc, receiver_username asc
            limit $1
            """,
            limit
        )
        return [dict(r) for r in rows]


@app.get("/api/thanks/recent")
async def get_recent_thanks(limit: int = 20):
    """Get recent thanks given"""
    assert pool is not None
    limit = max(1, min(limit, 100))  # Limit between 1 and 100
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select t.id, t.sender_username, t.receiver_username, t.created_at
            from public.thanks t
            order by t.created_at desc
            limit $1
            """,
            limit
        )
        return [dict(r) for r in rows]


def normalize_telegram_username(input_text: str) -> str | None:
    """
    Normalize various Telegram username formats to a clean username.
    Accepts: @username, username, t.me/username, https://t.me/username, or numeric user_id
    Returns: clean username (without @, t.me/, etc.) or user_id as string
    """
    if not input_text:
        return None
    
    # Remove whitespace
    text = input_text.strip()
    
    # Handle t.me links
    if 't.me/' in text:
        # Extract username from t.me/username
        parts = text.split('t.me/')
        if len(parts) > 1:
            text = parts[-1].split('?')[0].split('#')[0]  # Remove query params and fragments
    
    # Remove @ prefix
    if text.startswith('@'):
        text = text[1:]
    
    # Remove any remaining protocol or domain
    if text.startswith('https://') or text.startswith('http://'):
        text = text.split('/')[-1]
    
    # Clean up any remaining unwanted characters
    text = text.split('?')[0].split('#')[0]  # Remove query params and fragments
    
    return text if text else None


@app.post("/api/validate-telegram-username", response_model=TelegramValidationResponse)
async def validate_telegram_username(request: TelegramValidationRequest):
    """Validate Telegram username and fetch user information"""
    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=500, detail="Telegram token not configured")
    
    input_text = request.username.strip()
    
    # Basic validation
    if not input_text:
        return TelegramValidationResponse(
            is_valid=False,
            message="Username cannot be empty"
        )
    
    # Normalize the username from various formats
    normalized_username = normalize_telegram_username(input_text)
    
    if not normalized_username:
        return TelegramValidationResponse(
            is_valid=False,
            message="Could not extract username from input. Please use: @username, username, or t.me/username"
        )
    
    # Validate username format (Telegram usernames: 5-32 chars, alphanumeric + underscore)
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', normalized_username):
        return TelegramValidationResponse(
            is_valid=False,
            message=f"Invalid username format: '{normalized_username}'. Must be 5-32 characters, alphanumeric and underscores only"
        )
    
    try:
        # Check if username already exists in database
        assert pool is not None
        async with pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT user_id, user_telegram_link FROM users WHERE user_telegram_link = $1",
                normalized_username
            )
            
            if existing_user:
                return TelegramValidationResponse(
                    user_id=existing_user['user_id'],
                    chat_id=existing_user['user_id'],  # chat_id is typically same as user_id for private chats
                    username=normalized_username,
                    normalized_username=normalized_username,
                    is_valid=True,
                    message="Username found in database"
                )
        
        # Try to get user information from Telegram using the Bot API
        # This will work if the user has interacted with the bot before
        if TELEGRAM_TOKEN:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Try to get user info using getChat method
                    # Note: This only works if the user has interacted with the bot
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat"
                    data = {"chat_id": f"@{normalized_username}"}
                    
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("ok") and result.get("result"):
                                chat_info = result["result"]
                                first_name = chat_info.get("first_name", "")
                                last_name = chat_info.get("last_name", "")
                                
                                return TelegramValidationResponse(
                                    username=normalized_username,
                                    normalized_username=normalized_username,
                                    first_name=first_name,
                                    last_name=last_name,
                                    is_valid=True,
                                    message="User information retrieved from Telegram"
                                )
            except Exception as e:
                print(f"Error fetching user info from Telegram: {e}")
        
        # Fallback: just validate format
        return TelegramValidationResponse(
            username=normalized_username,
            normalized_username=normalized_username,
            is_valid=True,
            message="Username format is valid. Note: User ID will be available after user interacts with the bot."
        )
        
    except Exception as e:
        return TelegramValidationResponse(
            is_valid=False,
            message=f"Error validating username: {str(e)}"
        )


@app.post("/api/validate-linkedin-profile", response_model=LinkedInValidationResponse)
async def validate_linkedin_profile(request: LinkedInValidationRequest):
    """Validate LinkedIn URL and extract basic profile information"""
    import re
    from urllib.parse import urlparse
    
    url = request.url.strip()
    
    # Basic validation
    if not url:
        return LinkedInValidationResponse(
            is_valid=False,
            message="LinkedIn URL cannot be empty"
        )
    
    # Handle empty/skip values
    skip_values = ["", "none", "n/a", "na", "недоступен", "отсутствует", "пусто", "not available", "не указан"]
    if url.lower() in skip_values:
        return LinkedInValidationResponse(
            is_valid=True,
            message="LinkedIn profile skipped",
            profile_data={}
        )
    
    # Validate LinkedIn URL format
    try:
        # Remove @ symbol if present at the beginning
        if url.startswith('@'):
            url = url[1:]
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        
        if parsed.netloc.lower() not in ['linkedin.com', 'www.linkedin.com']:
            return LinkedInValidationResponse(
                is_valid=False,
                message="URL must be from LinkedIn.com"
            )
        
        if not parsed.path.startswith(('/in/', '/pub/')):
            return LinkedInValidationResponse(
                is_valid=False,
                message="LinkedIn URL must be a profile (/in/ or /pub/)"
            )
        
        # Extract username from path
        username = parsed.path.split('/')[-1]
        # LinkedIn usernames can contain various characters, so we'll be more permissive
        if not username or len(username) < 2 or len(username) > 100:
            return LinkedInValidationResponse(
                is_valid=False,
                message="Invalid LinkedIn profile identifier"
            )
        
        # Basic profile data structure
        # Note: LinkedIn has strict anti-scraping measures, so we can't extract profile data
        profile_data = {
            "url": url,
            "username": username,
            "name": None,
            "headline": None,
            "location": None,
            "summary": None
        }
        
        return LinkedInValidationResponse(
            is_valid=True,
            message="LinkedIn URL is valid and properly formatted",
            profile_data=profile_data
        )
        
    except Exception as e:
        return LinkedInValidationResponse(
            is_valid=False,
            message=f"Error validating LinkedIn URL: {str(e)}"
        )


# Notification Management Endpoints
class NotificationCreate(BaseModel):
    message_text: str
    image_url: str | None = None  # Optional image URL for photo notifications
    scheduled_at: datetime | None = None
    recipient_type: str = "all"  # 'all', 'user', 'group'
    recipient_ids: List[int] | None = None


class NotificationUpdate(BaseModel):
    message_text: str | None = None
    image_url: str | None = None  # Optional image URL for photo notifications
    scheduled_at: datetime | None = None
    status: str | None = None  # 'scheduled', 'sent', 'cancelled'
    recipient_type: str | None = None
    recipient_ids: List[int] | None = None


class NotificationResponse(BaseModel):
    id: int
    message_text: str
    image_url: str | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    status: str
    recipient_type: str
    recipient_ids: List[int] | None = None
    sent_count: int | None = 0
    failed_count: int | None = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


@app.get("/api/notifications", response_model=List[NotificationResponse])
async def get_notifications():
    """Get all notifications"""
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, message_text, image_url, scheduled_at, sent_at, status, recipient_type, recipient_ids, 
                   COALESCE(sent_count, 0) as sent_count, COALESCE(failed_count, 0) as failed_count, error_message,
                   created_at, updated_at
            FROM notifications
            ORDER BY created_at DESC
            LIMIT 100
            """
        )
        notifications = []
        for row in rows:
            notifications.append({
                "id": row["id"],
                "message_text": row["message_text"],
                "image_url": row.get("image_url"),
                "scheduled_at": row["scheduled_at"],
                "sent_at": row["sent_at"],
                "status": row["status"],
                "recipient_type": row["recipient_type"],
                "recipient_ids": row["recipient_ids"] if row["recipient_ids"] else [],
                "sent_count": row.get("sent_count", 0),
                "failed_count": row.get("failed_count", 0),
                "error_message": row.get("error_message"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        return notifications


@app.get("/api/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: int):
    """Get a specific notification by ID"""
    assert pool is not None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, message_text, image_url, scheduled_at, sent_at, status, recipient_type, recipient_ids,
                   COALESCE(sent_count, 0) as sent_count, COALESCE(failed_count, 0) as failed_count, error_message,
                   created_at, updated_at
            FROM notifications WHERE id = $1
            """,
            notification_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {
            "id": row["id"],
            "message_text": row["message_text"],
            "image_url": row.get("image_url"),
            "scheduled_at": row["scheduled_at"],
            "sent_at": row["sent_at"],
            "status": row["status"],
            "recipient_type": row["recipient_type"],
            "recipient_ids": row["recipient_ids"] if row["recipient_ids"] else [],
            "sent_count": row.get("sent_count", 0),
            "failed_count": row.get("failed_count", 0),
            "error_message": row.get("error_message"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.post("/api/notifications", response_model=NotificationResponse)
async def create_notification(notification_data: NotificationCreate):
    """Create a new notification. If scheduled_at is NULL, it will be sent immediately."""
    assert pool is not None
    
    # Validate recipient_type
    if notification_data.recipient_type not in ["all", "user", "group", "user_group"]:
        raise HTTPException(status_code=400, detail="recipient_type must be 'all', 'user', 'group', or 'user_group'")
    
    # Validate recipient_ids
    if notification_data.recipient_type == "user" and not notification_data.recipient_ids:
        raise HTTPException(status_code=400, detail="recipient_ids required when recipient_type is 'user'")
    if notification_data.recipient_type == "user_group" and not notification_data.recipient_ids:
        raise HTTPException(status_code=400, detail="recipient_ids (group IDs) required when recipient_type is 'user_group'")
    # For 'group' type, recipient_ids is not needed - uses TELEGRAM_GROUP_ID from env
    
    async with pool.acquire() as conn:
        # If scheduled_at is NULL (send now), create with status 'scheduled' and scheduled_at NULL
        # The scheduler will pick it up immediately and send it, then mark it as 'sent'
        # If scheduled_at has a date, create with status 'scheduled' (planned for future)
        # Always start with 'scheduled' status - the scheduler will mark as 'sent' after actual sending
        initial_status = 'scheduled'
        sent_at_value = None  # Will be set by the scheduler after sending
        
        row = await conn.fetchrow(
            """
            INSERT INTO notifications (message_text, image_url, scheduled_at, status, recipient_type, recipient_ids, sent_at, sent_count, failed_count, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 0, 0, NOW(), NOW())
            RETURNING id, message_text, image_url, scheduled_at, sent_at, status, recipient_type, recipient_ids, 
                      COALESCE(sent_count, 0) as sent_count, COALESCE(failed_count, 0) as failed_count, error_message,
                      created_at, updated_at
            """,
            notification_data.message_text,
            notification_data.image_url,
            notification_data.scheduled_at,
            initial_status,
            notification_data.recipient_type,
            notification_data.recipient_ids,
            sent_at_value
        )
        
        return {
            "id": row["id"],
            "message_text": row["message_text"],
            "image_url": row.get("image_url"),
            "scheduled_at": row["scheduled_at"],
            "sent_at": row["sent_at"],
            "status": row["status"],
            "recipient_type": row["recipient_type"],
            "recipient_ids": row["recipient_ids"] if row["recipient_ids"] else [],
            "sent_count": row.get("sent_count", 0),
            "failed_count": row.get("failed_count", 0),
            "error_message": row.get("error_message"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.put("/api/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(notification_id: int, notification_data: NotificationUpdate):
    """Update an existing notification"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if notification exists
        existing = await conn.fetchrow(
            "SELECT id FROM notifications WHERE id = $1",
            notification_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        for field, value in notification_data.dict(exclude_unset=True).items():
            if field == "recipient_ids" and value is not None:
                update_fields.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            elif value is not None:
                update_fields.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated_at
        update_fields.append("updated_at = NOW()")
        
        # Add notification_id for WHERE clause
        values.append(notification_id)
        
        query = f"""
            UPDATE notifications 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, message_text, image_url, scheduled_at, sent_at, status, recipient_type, recipient_ids,
                      COALESCE(sent_count, 0) as sent_count, COALESCE(failed_count, 0) as failed_count, error_message,
                      created_at, updated_at
        """
        
        row = await conn.fetchrow(query, *values)
        return {
            "id": row["id"],
            "message_text": row["message_text"],
            "image_url": row.get("image_url"),
            "scheduled_at": row["scheduled_at"],
            "sent_at": row["sent_at"],
            "status": row["status"],
            "recipient_type": row["recipient_type"],
            "recipient_ids": row["recipient_ids"] if row["recipient_ids"] else [],
            "sent_count": row.get("sent_count", 0),
            "failed_count": row.get("failed_count", 0),
            "error_message": row.get("error_message"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: int):
    """Delete or cancel a notification"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if notification exists
        existing = await conn.fetchrow(
            "SELECT id, status FROM notifications WHERE id = $1",
            notification_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Delete completely - for both sent and non-sent notifications
        await conn.execute("DELETE FROM notifications WHERE id = $1", notification_id)
        return {"message": "Notification deleted successfully"}


@app.get("/api/telegram-group-info")
async def get_telegram_group_info():
    """Get Telegram group name by ID"""
    group_id = os.getenv("TELEGRAM_GROUP_ID")
    if not group_id or not TELEGRAM_TOKEN:
        return {"group_name": None, "error": "TELEGRAM_GROUP_ID or TELEGRAM_TOKEN not configured"}
    
    try:
        # Get group info from Telegram API
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat"
        data = {"chat_id": int(group_id)}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=5.0)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok") and result.get("result"):
                chat_info = result["result"]
                group_name = chat_info.get("title") or chat_info.get("first_name") or f"Group {group_id}"
                return {"group_name": group_name, "group_id": group_id}
            else:
                return {"group_name": None, "error": "Failed to get group information from Telegram"}
    except Exception as e:
        return {"group_name": None, "error": f"Error fetching group info: {str(e)}"}


class CheckMessageAvailabilityRequest(BaseModel):
    user_ids: List[int]


class UserMessageAvailability(BaseModel):
    user_id: int
    can_send_message: bool
    error: Optional[str] = None


class CheckMessageAvailabilityResponse(BaseModel):
    results: List[UserMessageAvailability]


@app.post("/api/users/check-message-availability", response_model=CheckMessageAvailabilityResponse)
async def check_message_availability(request: CheckMessageAvailabilityRequest):
    """Check if bot can send messages to users via Telegram API"""
    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_TOKEN not configured")
    
    results = []
    
    # Get chat_id information from database and check notification history
    assert pool is not None
    chat_id_map = {}
    users_with_recent_critical_failures = set()
    async with pool.acquire() as conn:
        # Get chat_id for users (for logging purposes)
        rows = await conn.fetch(
            "SELECT user_id, chat_id FROM users WHERE user_id = ANY($1)",
            request.user_ids
        )
        chat_id_map = {row['user_id']: row['chat_id'] for row in rows}
        
        # Check for users with RECENT critical failures (last 7 days) that indicate they cannot receive messages
        # We only look for specific errors that definitively mean the user cannot receive messages:
        # - "can't initiate conversation" errors
        # - All messages failed with no successes (failed_count > 0 AND sent_count = 0)
        # This helps catch cases where getChat might succeed but user actually cannot receive messages
        # NOTE: We use a shorter time window (7 days) and only for critical errors to avoid false positives
        # IMPORTANT: Only check if notifications exist for these users to avoid false positives on new systems
        critical_failure_rows = await conn.fetch(
            """
            SELECT DISTINCT unnest(recipient_ids) as user_id
            FROM notifications
            WHERE recipient_type = 'user'
              AND recipient_ids IS NOT NULL
              AND recipient_ids && $1::bigint[]
              AND updated_at > NOW() - INTERVAL '7 days'
              AND (
                  -- All messages failed with no successes (user likely blocked bot or never started conversation)
                  (failed_count > 0 AND sent_count = 0)
                  -- OR specific errors indicating user cannot receive messages
                  OR (error_message IS NOT NULL AND (
                      error_message ILIKE '%can''t initiate conversation%'
                      OR error_message ILIKE '%bot can''t initiate conversation%'
                      OR error_message ILIKE '%Forbidden: bot can''t initiate%'
                      OR error_message ILIKE '%chat not found%'
                      OR error_message ILIKE '%user not found%'
                  ))
              )
            """,
            request.user_ids
        )
        users_with_recent_critical_failures = {row['user_id'] for row in critical_failure_rows}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChat"
        
        for user_id in request.user_ids:
            try:
                # Check if this is a temporary user ID (negative number)
                # Temporary IDs are used for users added via admin panel before they interact with bot
                # getChat will not work for temporary IDs - they need to be migrated to real Telegram IDs first
                if user_id < 0:
                    # This is a temporary user ID - cannot check via getChat
                    # These users likely haven't started conversation with bot yet
                    results.append(UserMessageAvailability(
                        user_id=user_id,
                        can_send_message=False,
                        error="User hasn't started conversation with bot yet"
                    ))
                    continue
                
                # Try to get chat info - if successful, we can send messages to this user
                # Note: getChat only works for private chats if user has started conversation with bot
                data = {"chat_id": user_id}
                response = await client.post(url, json=data, timeout=5.0)
                result = response.json()
                
                if result.get("ok") and result.get("result"):
                    # Check if it's a private chat (type == "private")
                    # For private chats, if getChat succeeds, we can send messages
                    chat_info = result.get("result", {})
                    chat_type = chat_info.get("type", "")
                    
                    user_chat_id = chat_id_map.get(user_id)
                    has_critical_failures = user_id in users_with_recent_critical_failures
                    
                    if chat_type == "private":
                        # getChat succeeded for private chat - this is a good sign
                        # However, if user has RECENT critical failures (last 7 days) with specific errors
                        # that indicate they cannot receive messages, we should trust the history over getChat
                        # This handles cases where getChat might succeed but user actually blocked the bot
                        # or never started conversation (getChat can sometimes succeed even if we can't send)
                        if user_id in users_with_recent_critical_failures:
                            # User has recent critical failures - trust history over getChat success
                            # This catches cases where getChat succeeds but user cannot actually receive messages
                            results.append(UserMessageAvailability(
                                user_id=user_id,
                                can_send_message=False,
                                error="User has recent notification failures indicating messages cannot be delivered"
                            ))
                        else:
                            # getChat succeeded and no recent critical failures - can send messages
                            results.append(UserMessageAvailability(
                                user_id=user_id,
                                can_send_message=True
                            ))
                    else:
                        # For groups/channels, we need different handling
                        # But for notification system, we primarily care about private chats
                        results.append(UserMessageAvailability(
                            user_id=user_id,
                            can_send_message=True
                        ))
                else:
                    # getChat failed - check error code and database chat_id to determine availability
                    error_code = result.get("error_code", 0)
                    error_msg = result.get("description", "Unknown error")
                    
                    user_chat_id = chat_id_map.get(user_id)
                    
                    # IMPORTANT: If user has chat_id in database, they've interacted with bot before
                    # getChat might fail for various reasons (bot blocked, chat deleted, etc.)
                    # but if chat_id exists, there's a chance they can still receive messages
                    # We'll trust the database chat_id over getChat failure
                    if user_chat_id is not None and user_chat_id == user_id:
                        # User has chat_id matching user_id - they've interacted with bot
                        # Even if getChat fails, they might still be contactable
                        # Mark as can_send=True if chat_id exists (they interacted with bot)
                        results.append(UserMessageAvailability(
                            user_id=user_id,
                            can_send_message=True
                        ))
                    else:
                        # No chat_id in DB or chat_id doesn't match - user probably hasn't started conversation
                        # OR error is definitive (403 Forbidden = blocked)
                        can_send = False
                        error_lower = error_msg.lower() if error_msg else ""
                        
                        if error_code == 403:
                            # 403 Forbidden - user blocked bot (definitive)
                            can_send = False
                        elif "user not found" in error_lower:
                            # User doesn't exist in Telegram (definitive)
                            can_send = False
                        else:
                            # getChat failed and no chat_id - user hasn't started conversation
                            can_send = False
                        
                        results.append(UserMessageAvailability(
                            user_id=user_id,
                            can_send_message=can_send,
                            error=error_msg
                        ))
            except httpx.HTTPStatusError as e:
                # HTTP error - cannot send message
                response_text = ""
                try:
                    # Try to parse JSON response
                    error_data = e.response.json()
                    error_msg = error_data.get("description", "") if isinstance(error_data, dict) else ""
                    response_text = error_msg[:200] if error_msg else str(e)[:200]
                except:
                    try:
                        response_text = e.response.text[:200]
                    except:
                        response_text = str(e)[:200]
                
                # Any HTTP error (400, 403, etc.) means cannot send message
                results.append(UserMessageAvailability(
                    user_id=user_id,
                    can_send_message=False,
                    error=f"HTTP {e.response.status_code}: {response_text}"
                ))
            except Exception as e:
                # Other errors - assume not available
                results.append(UserMessageAvailability(
                    user_id=user_id,
                    can_send_message=False,
                    error=str(e)[:100]
                ))
    
    return CheckMessageAvailabilityResponse(results=results)


@app.post("/api/notifications/{notification_id}/send")
async def send_notification_now(notification_id: int):
    """Manually trigger sending a notification (if scheduled)"""
    # Set scheduled_at to now to trigger immediate sending by the scheduler
    # The scheduler checks every minute, so it will be sent within a minute
    assert pool is not None
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, status FROM notifications WHERE id = $1",
            notification_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if existing["status"] == "sent":
            raise HTTPException(status_code=400, detail="Notification already sent")
        
        # Set scheduled_at to NULL to trigger immediate sending by the scheduler
        # The scheduler processes notifications with scheduled_at IS NULL OR scheduled_at <= NOW()
        await conn.execute(
            "UPDATE notifications SET scheduled_at = NULL, updated_at = NOW() WHERE id = $1",
            notification_id
        )
        
        # Also trigger immediate sending by calling the scheduler function directly
        try:
            from bot.notifications import send_notification
            # This will be called asynchronously, but we trigger it here
            # The scheduler will also pick it up within 1 minute
            return {"message": "Notification will be sent immediately"}
        except Exception as e:
            # If direct call fails, scheduler will still pick it up
            return {"message": "Notification will be sent shortly (within 1 minute)"}


class NotificationSettings(BaseModel):
    enabled: bool

@app.put("/api/users/{user_id}/notifications")
async def update_user_notifications(user_id: int, settings: NotificationSettings):
    """Update user notification preferences"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        await conn.execute(
            "UPDATE users SET notifications_enabled = $1, updated_at = NOW() WHERE user_id = $2",
            settings.enabled,
            user_id
        )
        
        return {"message": f"Notifications {'enabled' if settings.enabled else 'disabled'} for user"}


# ==================== User Groups API ====================

class UserGroupCreate(BaseModel):
    name: str


class UserGroupResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class UserGroupUpdate(BaseModel):
    name: str


@app.get("/api/groups", response_model=List[UserGroupResponse])
async def get_groups():
    """Get all user groups"""
    assert pool is not None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, created_at, updated_at
            FROM user_groups
            ORDER BY name ASC
            """
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


@app.get("/api/groups/{group_id}", response_model=UserGroupResponse)
async def get_group(group_id: int):
    """Get a specific group by ID"""
    assert pool is not None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, created_at, updated_at
            FROM user_groups
            WHERE id = $1
            """,
            group_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Group not found")
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.post("/api/groups", response_model=UserGroupResponse)
async def create_group(group_data: UserGroupCreate):
    """Create a new user group"""
    assert pool is not None
    if not group_data.name or not group_data.name.strip():
        raise HTTPException(status_code=400, detail="Group name cannot be empty")
    
    async with pool.acquire() as conn:
        # Check if group with same name already exists
        existing = await conn.fetchrow(
            "SELECT id FROM user_groups WHERE LOWER(name) = LOWER($1)",
            group_data.name.strip()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Group with this name already exists")
        
        row = await conn.fetchrow(
            """
            INSERT INTO user_groups (name, created_at, updated_at)
            VALUES ($1, NOW(), NOW())
            RETURNING id, name, created_at, updated_at
            """,
            group_data.name.strip()
        )
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.put("/api/groups/{group_id}", response_model=UserGroupResponse)
async def update_group(group_id: int, group_data: UserGroupUpdate):
    """Update an existing group"""
    assert pool is not None
    if not group_data.name or not group_data.name.strip():
        raise HTTPException(status_code=400, detail="Group name cannot be empty")
    
    async with pool.acquire() as conn:
        # Check if group exists
        existing = await conn.fetchrow(
            "SELECT id FROM user_groups WHERE id = $1",
            group_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Check if another group with same name exists
        duplicate = await conn.fetchrow(
            "SELECT id FROM user_groups WHERE LOWER(name) = LOWER($1) AND id != $2",
            group_data.name.strip(),
            group_id
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Group with this name already exists")
        
        row = await conn.fetchrow(
            """
            UPDATE user_groups
            SET name = $1, updated_at = NOW()
            WHERE id = $2
            RETURNING id, name, created_at, updated_at
            """,
            group_data.name.strip(),
            group_id
        )
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


@app.delete("/api/groups/{group_id}")
async def delete_group(group_id: int):
    """Delete a group (will also remove all memberships)"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if group exists
        existing = await conn.fetchrow(
            "SELECT id FROM user_groups WHERE id = $1",
            group_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Delete group (CASCADE will remove memberships)
        await conn.execute("DELETE FROM user_groups WHERE id = $1", group_id)
        return {"message": "Group deleted successfully"}


class UserGroupMembershipRequest(BaseModel):
    group_ids: List[int]


@app.get("/api/users/{user_id}/groups", response_model=List[UserGroupResponse])
async def get_user_groups(user_id: int):
    """Get all groups for a specific user"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if user exists
        user_exists = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        rows = await conn.fetch(
            """
            SELECT ug.id, ug.name, ug.created_at, ug.updated_at
            FROM user_groups ug
            INNER JOIN user_group_memberships ugm ON ug.id = ugm.group_id
            WHERE ugm.user_id = $1
            ORDER BY ug.name ASC
            """,
            user_id
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


@app.post("/api/users/{user_id}/groups", response_model=List[UserGroupResponse])
async def add_user_to_groups(user_id: int, request: UserGroupMembershipRequest):
    """Add user to one or more groups"""
    assert pool is not None
    if not request.group_ids:
        raise HTTPException(status_code=400, detail="group_ids cannot be empty")
    
    async with pool.acquire() as conn:
        # Check if user exists
        user_exists = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if all groups exist
        group_rows = await conn.fetch(
            "SELECT id FROM user_groups WHERE id = ANY($1)",
            request.group_ids
        )
        found_group_ids = {row['id'] for row in group_rows}
        missing_group_ids = set(request.group_ids) - found_group_ids
        if missing_group_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Groups not found: {list(missing_group_ids)}"
            )
        
        # Add memberships (ignore duplicates)
        for group_id in request.group_ids:
            await conn.execute(
                """
                INSERT INTO user_group_memberships (user_id, group_id, created_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id, group_id) DO NOTHING
                """,
                user_id,
                group_id
            )
        
        # Return updated list of user's groups
        rows = await conn.fetch(
            """
            SELECT ug.id, ug.name, ug.created_at, ug.updated_at
            FROM user_groups ug
            INNER JOIN user_group_memberships ugm ON ug.id = ugm.group_id
            WHERE ugm.user_id = $1
            ORDER BY ug.name ASC
            """,
            user_id
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


@app.delete("/api/users/{user_id}/groups/{group_id}")
async def remove_user_from_group(user_id: int, group_id: int):
    """Remove user from a group"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if user exists
        user_exists = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id
        )
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if group exists
        group_exists = await conn.fetchrow(
            "SELECT id FROM user_groups WHERE id = $1",
            group_id
        )
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Remove membership
        result = await conn.execute(
            "DELETE FROM user_group_memberships WHERE user_id = $1 AND group_id = $2",
            user_id,
            group_id
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="User is not a member of this group")
        
        return {"message": "User removed from group successfully"}


@app.get("/api/groups/{group_id}/users")
async def get_group_users(group_id: int):
    """Get all users in a specific group"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if group exists
        group_exists = await conn.fetchrow(
            "SELECT id, name FROM user_groups WHERE id = $1",
            group_id
        )
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        rows = await conn.fetch(
            """
            SELECT u.user_id, u.intro_name, u.state, u.notifications_enabled, u.finishedonboarding
            FROM users u
            INNER JOIN user_group_memberships ugm ON u.user_id = ugm.user_id
            WHERE ugm.group_id = $1
            ORDER BY u.intro_name ASC NULLS LAST
            """,
            group_id
        )
        return {
            "group_id": group_id,
            "group_name": group_exists["name"],
            "users": [
                {
                    "user_id": row["user_id"],
                    "intro_name": row["intro_name"],
                    "state": row["state"],
                    "notifications_enabled": row["notifications_enabled"],
                    "finishedonboarding": row["finishedonboarding"]
                }
                for row in rows
            ]
        }


@app.get("/api/groups/{group_id}/status")
async def get_group_status(group_id: int):
    """Get group status with information about users who may have issues receiving notifications"""
    assert pool is not None
    async with pool.acquire() as conn:
        # Check if group exists
        group_exists = await conn.fetchrow(
            "SELECT id, name FROM user_groups WHERE id = $1",
            group_id
        )
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all users in group
        all_users = await conn.fetch(
            """
            SELECT u.user_id, u.intro_name, u.state, u.notifications_enabled, u.finishedonboarding, u.user_telegram_link
            FROM users u
            INNER JOIN user_group_memberships ugm ON u.user_id = ugm.user_id
            WHERE ugm.group_id = $1
            """,
            group_id
        )
        
        user_ids = [user['user_id'] for user in all_users]
        
        # Check for users with recent critical failures (cannot receive messages via Telegram)
        users_with_recent_critical_failures = set()
        if user_ids:
            critical_failure_rows = await conn.fetch(
                """
                SELECT DISTINCT unnest(recipient_ids) as user_id
                FROM notifications
                WHERE recipient_type = 'user'
                  AND recipient_ids IS NOT NULL
                  AND recipient_ids && $1::bigint[]
                  AND updated_at > NOW() - INTERVAL '7 days'
                  AND (
                      -- All messages failed with no successes (user likely blocked bot or never started conversation)
                      (failed_count > 0 AND sent_count = 0)
                      -- OR specific errors indicating user cannot receive messages
                      OR (error_message IS NOT NULL AND (
                          error_message ILIKE '%can''t initiate conversation%'
                          OR error_message ILIKE '%bot can''t initiate conversation%'
                          OR error_message ILIKE '%Forbidden: bot can''t initiate%'
                          OR error_message ILIKE '%chat not found%'
                          OR error_message ILIKE '%user not found%'
                      ))
                  )
                """,
                user_ids
            )
            users_with_recent_critical_failures = {row['user_id'] for row in critical_failure_rows}
        
        # Filter users who may have issues
        problematic_users = []
        for user in all_users:
            issues = []
            # Critical: Check if user has no Telegram link at all
            if not user['user_telegram_link'] or user['user_telegram_link'].strip() == '':
                issues.append("no_telegram_link")
            # Critical: Check if user_id is negative (groups have negative IDs, private chats have positive)
            if user['user_id'] < 0:
                issues.append("negative_user_id")
            # Check if notifications are disabled (will be filtered out during sending)
            if not user['notifications_enabled']:
                issues.append("notifications_disabled")
            if user['state'] != 'ACTIVE':
                issues.append(f"state_{user['state'].lower()}")
            if not user['finishedonboarding']:
                issues.append("not_finished_onboarding")
            # Check if user has recent critical failures (cannot receive messages)
            if user['user_id'] in users_with_recent_critical_failures:
                issues.append("cannot_receive_messages")
            
            if issues:
                problematic_users.append({
                    "user_id": user['user_id'],
                    "intro_name": user['intro_name'],
                    "issues": issues
                })
        
        # Status: OK if no problematic users, NOT_OK if there are problematic users
        status = "OK" if len(problematic_users) == 0 else "NOT_OK"

        # Return up to 3 problematic users for tooltip
        return {
            "group_id": group_id,
            "group_name": group_exists["name"],
            "status": status,
            "total_users": len(all_users),
            "problematic_users_count": len(problematic_users),
            "problematic_users": problematic_users[:3]  # Max 3 for tooltip
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TMA (Telegram Mini App) endpoints
# Auth: X-Telegram-Init-Data header validated via HMAC-SHA256
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import hmac as hmac_module
import json as json_module
from urllib.parse import parse_qsl
from fastapi.responses import StreamingResponse


def _validate_tma_init_data(init_data: str) -> Optional[dict]:
    """Validate Telegram Web App initData and return user dict, or None if invalid."""
    if not TELEGRAM_TOKEN or not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac_module.new(
            b"WebAppData", TELEGRAM_TOKEN.encode(), hashlib.sha256
        ).digest()
        expected = hmac_module.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if expected != received_hash:
            return None
        return json_module.loads(parsed.get("user", "{}"))
    except Exception:
        return None


async def _get_tma_user(x_telegram_init_data: str = Header(default="")) -> dict:
    """FastAPI dependency: validate TMA auth and return Telegram user dict."""
    if DEV_TMA_BYPASS and not x_telegram_init_data:
        return {
            "id": DEV_TMA_USER_ID,
            "first_name": "Local",
            "last_name": "Tester",
            "username": "dev_tma_user",
        }

    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data header")
    user = _validate_tma_init_data(x_telegram_init_data)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid Telegram init data")
    if TMA_ALLOWED_USER_IDS and int(user.get("id", 0)) not in TMA_ALLOWED_USER_IDS:
        raise HTTPException(status_code=403, detail="TMA access is not enabled for this user")
    return user


def _member_row_to_dict(row: dict) -> dict:
    """Convert a DB user row to TMA member response."""
    d = dict(row)
    # Resolve photo
    if d.get("intro_image"):
        if is_base64_image(d["intro_image"]):
            d["intro_image"] = get_data_url_from_base64(d["intro_image"])
        elif not d["intro_image"].startswith(("http://", "https://", "data:")):
            d["intro_image"] = None  # Will be fetched via /tma/photo/{user_id}
    # Convert date
    if d.get("intro_birthday") is not None:
        d["intro_birthday"] = str(d["intro_birthday"])
    # Defaults
    d.setdefault("thanks_received", 0)
    d.setdefault("meetings_completed", 0)
    d.setdefault("offer", None)
    d.setdefault("request_text", None)
    return d


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _normalize_vector(raw: Any) -> Optional[List[float]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        try:
            return [float(v) for v in raw]
        except (TypeError, ValueError):
            return None
    if isinstance(raw, tuple):
        try:
            return [float(v) for v in raw]
        except (TypeError, ValueError):
            return None
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("{") and text.endswith("}"):
            parts = [part.strip() for part in text[1:-1].split(",") if part.strip()]
            try:
                return [float(v) for v in parts]
            except ValueError:
                return None
    return None


async def _get_pending_meeting_id(conn: asyncpg.Connection, user_id: int) -> Optional[int]:
    return await conn.fetchval(
        """
        SELECT m.id
        FROM public.meetings m
        WHERE (m.user_1_id = $1 OR m.user_2_id = $1)
          AND m.status = 'new'
          AND NOT EXISTS (
              SELECT 1
              FROM public.meetings newer
              WHERE LEAST(newer.user_1_id, newer.user_2_id) = LEAST(m.user_1_id, m.user_2_id)
                AND GREATEST(newer.user_1_id, newer.user_2_id) = GREATEST(m.user_1_id, m.user_2_id)
                AND newer.id > m.id
          )
        ORDER BY m.created_at DESC
        LIMIT 1
        """,
        user_id,
    )


async def _get_matchable_user_row(conn: asyncpg.Connection, user_id: int) -> Optional[dict]:
    row = await conn.fetchrow(
        """
        SELECT user_id, vector_description
        FROM public.users
        WHERE user_id = $1
          AND finishedonboarding = true
          AND state = 'ACTIVE'
          AND vector_description IS NOT NULL
          AND intro_description IS NOT NULL
          AND length(trim(intro_description)) >= 10
          AND (matches_disabled IS NULL OR matches_disabled = false)
        """,
        user_id,
    )
    return dict(row) if row else None


async def _has_block_between(conn: asyncpg.Connection, user_id: int, other_user_id: int) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1
        FROM public.match_blocks
        WHERE (user_id = $1 AND blocked_user_id = $2)
           OR (user_id = $2 AND blocked_user_id = $1)
        LIMIT 1
        """,
        user_id,
        other_user_id,
    )
    return row is not None


async def _has_recent_met_meeting(
    conn: asyncpg.Connection,
    user_id: int,
    other_user_id: int,
    months: int = 6,
) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1
        FROM public.meetings
        WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
          AND status = 'met'
          AND last_updated >= NOW() - (INTERVAL '1 month' * $3)
        LIMIT 1
        """,
        user_id,
        other_user_id,
        months,
    )
    return row is not None


async def _has_already_known_meeting(
    conn: asyncpg.Connection,
    user_id: int,
    other_user_id: int,
) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1
        FROM public.meetings
        WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
          AND already_known = true
        LIMIT 1
        """,
        user_id,
        other_user_id,
    )
    return row is not None


async def _candidate_has_pending_meeting(conn: asyncpg.Connection, user_id: int) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1
        FROM public.meetings
        WHERE (user_1_id = $1 OR user_2_id = $1) AND status = 'new'
        LIMIT 1
        """,
        user_id,
    )
    return row is not None


async def _find_best_match_for_user(
    conn: asyncpg.Connection,
    user_id: int,
    min_similarity_threshold: float = 0.3,
) -> Optional[int]:
    me = await _get_matchable_user_row(conn, user_id)
    if not me:
        raise HTTPException(
            status_code=400,
            detail="Complete your profile to use Match",
        )

    my_vector = _normalize_vector(me.get("vector_description"))
    if not my_vector:
        raise HTTPException(
            status_code=400,
            detail="Complete your profile to use Match",
        )

    candidates = await conn.fetch(
        """
        SELECT user_id, vector_description
        FROM public.users
        WHERE user_id != $1
          AND finishedonboarding = true
          AND state = 'ACTIVE'
          AND vector_description IS NOT NULL
          AND intro_description IS NOT NULL
          AND length(trim(intro_description)) >= 10
          AND (matches_disabled IS NULL OR matches_disabled = false)
        """,
        user_id,
    )

    best_user_id: Optional[int] = None
    best_score = -1.0

    for candidate_row in candidates:
        candidate = dict(candidate_row)
        candidate_id = int(candidate["user_id"])

        if await _candidate_has_pending_meeting(conn, candidate_id):
            continue
        if await _has_block_between(conn, user_id, candidate_id):
            continue
        if await _has_recent_met_meeting(conn, user_id, candidate_id, months=6):
            continue
        if await _has_already_known_meeting(conn, user_id, candidate_id):
            continue

        candidate_vector = _normalize_vector(candidate.get("vector_description"))
        if not candidate_vector:
            continue

        similarity = _cosine_similarity(my_vector, candidate_vector)
        if similarity >= min_similarity_threshold and similarity > best_score:
            best_score = similarity
            best_user_id = candidate_id

    return best_user_id


# ── Photo proxy ───────────────────────────────────────────────────────────────

@app.get("/tma/photo/{user_id}")
async def tma_get_photo(user_id: int):
    """Proxy Telegram profile photo for TMA display."""
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT intro_image FROM public.users WHERE user_id=$1", user_id
        )
    if not row or not row["intro_image"]:
        raise HTTPException(status_code=404, detail="No photo")

    image_data = row["intro_image"]

    if is_base64_image(image_data):
        import base64 as b64
        raw = b64.b64decode(image_data)
        media = "image/jpeg"
        if raw.startswith(b"\x89PNG"):
            media = "image/png"
        return Response(content=raw, media_type=media)

    if image_data.startswith(("http://", "https://")):
        return Response(
            status_code=302,
            headers={"Location": image_data},
        )

    # Telegram file ID — resolve and proxy
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            info = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
                params={"file_id": image_data},
            )
            info.raise_for_status()
            file_path = info.json()["result"]["file_path"]
            img = await client.get(
                f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            )
            img.raise_for_status()
            return Response(content=img.content, media_type="image/jpeg",
                            headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        raise HTTPException(status_code=404, detail="Photo unavailable")


# ── My profile ────────────────────────────────────────────────────────────────

@app.get("/tma/me")
async def tma_get_me(tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    user_id = tg_user.get("id")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.intro_name, u.intro_location, u.intro_description,
                   u.intro_linkedin, u.intro_hobbies_drivers, u.intro_skills,
                   u.field_of_activity, u.intro_birthday, u.intro_image,
                   u.user_telegram_link, u.offer, u.request_text,
                   COALESCE((SELECT COUNT(*) FROM public.thanks t WHERE t.receiver_username = u.username), 0) AS thanks_received,
                   COALESCE((SELECT COUNT(*) FROM public.meetings m WHERE (m.user_1_id = u.user_id OR m.user_2_id = u.user_id) AND m.status = 'met'), 0) AS meetings_completed
            FROM public.users u
            WHERE u.user_id = $1
            """,
            user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _member_row_to_dict(dict(row))


class TMAProfileUpdate(BaseModel):
    intro_name: Optional[str] = None
    intro_location: Optional[str] = None
    intro_description: Optional[str] = None
    intro_linkedin: Optional[str] = None
    intro_hobbies_drivers: Optional[str] = None
    intro_skills: Optional[str] = None
    field_of_activity: Optional[str] = None
    offer: Optional[str] = None
    request_text: Optional[str] = None


@app.put("/tma/me")
async def tma_update_me(body: TMAProfileUpdate, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    user_id = tg_user.get("id")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE public.users SET {set_clause}, updated_at=now() WHERE user_id=$1",
            user_id, *values,
        )
    return await tma_get_me(tg_user)


# ── Members directory ─────────────────────────────────────────────────────────

@app.get("/tma/members")
async def tma_get_members(
    search: Optional[str] = None,
    tg_user: dict = Depends(_get_tma_user),
):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        base_query = """
            SELECT u.user_id, u.intro_name, u.intro_location, u.intro_description,
                   u.intro_linkedin, u.intro_hobbies_drivers, u.intro_skills,
                   u.field_of_activity, u.intro_birthday, u.intro_image,
                   u.user_telegram_link, u.offer, u.request_text,
                   COALESCE((SELECT COUNT(*) FROM public.thanks t WHERE t.receiver_username = u.username), 0) AS thanks_received,
                   COALESCE((SELECT COUNT(*) FROM public.meetings m WHERE (m.user_1_id = u.user_id OR m.user_2_id = u.user_id) AND m.status = 'met'), 0) AS meetings_completed
            FROM public.users u
            WHERE u.finishedonboarding = true
              AND u.state = 'ACTIVE'
        """
        if search:
            base_query += """
              AND (
                u.intro_name ILIKE $1 OR u.intro_location ILIKE $1
                OR u.field_of_activity ILIKE $1 OR u.intro_skills ILIKE $1
                OR u.intro_description ILIKE $1
              )
            """
            base_query += " ORDER BY thanks_received DESC"
            rows = await conn.fetch(base_query, f"%{search}%")
        else:
            base_query += " ORDER BY thanks_received DESC"
            rows = await conn.fetch(base_query)
    return [_member_row_to_dict(dict(r)) for r in rows]


@app.get("/tma/members/{user_id}")
async def tma_get_member(user_id: int, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.intro_name, u.intro_location, u.intro_description,
                   u.intro_linkedin, u.intro_hobbies_drivers, u.intro_skills,
                   u.field_of_activity, u.intro_birthday, u.intro_image,
                   u.user_telegram_link, u.offer, u.request_text,
                   COALESCE((SELECT COUNT(*) FROM public.thanks t WHERE t.receiver_username = u.username), 0) AS thanks_received,
                   COALESCE((SELECT COUNT(*) FROM public.meetings m WHERE (m.user_1_id = u.user_id OR m.user_2_id = u.user_id) AND m.status = 'met'), 0) AS meetings_completed
            FROM public.users u
            WHERE u.user_id = $1
            """,
            user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    return _member_row_to_dict(dict(row))


# ── Matches / Meetings ────────────────────────────────────────────────────────

async def _get_meeting_with_matched_user(conn, meeting_id: int, my_user_id: int) -> Optional[dict]:
    row = await conn.fetchrow(
        """
        SELECT id, user_1_id, user_2_id, status, created_at
        FROM public.meetings WHERE id = $1
        """,
        meeting_id,
    )
    if not row:
        return None
    row = dict(row)
    other_id = row["user_2_id"] if row["user_1_id"] == my_user_id else row["user_1_id"]
    user_row = await conn.fetchrow(
        """
        SELECT u.user_id, u.intro_name, u.intro_location, u.intro_description,
               u.intro_linkedin, u.intro_hobbies_drivers, u.intro_skills,
               u.field_of_activity, u.intro_birthday, u.intro_image,
               u.user_telegram_link, u.offer, u.request_text,
               COALESCE((SELECT COUNT(*) FROM public.thanks t WHERE t.receiver_username = u.username), 0) AS thanks_received,
               COALESCE((SELECT COUNT(*) FROM public.meetings m WHERE (m.user_1_id = u.user_id OR m.user_2_id = u.user_id) AND m.status = 'met'), 0) AS meetings_completed
        FROM public.users u
        WHERE u.user_id = $1
        """,
        other_id,
    )
    row["matched_user"] = _member_row_to_dict(dict(user_row)) if user_row else {}
    row["created_at"] = str(row["created_at"])
    return row


@app.get("/tma/matches/pending")
async def tma_pending_match(tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    user_id = tg_user.get("id")
    async with pool.acquire() as conn:
        meeting_id = await _get_pending_meeting_id(conn, user_id)
        if not meeting_id:
            return None
        return await _get_meeting_with_matched_user(conn, meeting_id, user_id)


@app.post("/tma/matches/find")
async def tma_find_match(tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")

    user_id = int(tg_user.get("id"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            lock_ids = sorted([user_id])
            for lock_id in lock_ids:
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_id)

            existing_meeting_id = await _get_pending_meeting_id(conn, user_id)
            if existing_meeting_id:
                return await _get_meeting_with_matched_user(conn, existing_meeting_id, user_id)

            matched_user_id = await _find_best_match_for_user(conn, user_id)
            if matched_user_id is None:
                return None

            if matched_user_id != user_id:
                for lock_id in sorted([user_id, matched_user_id]):
                    await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_id)

            existing_meeting_id = await _get_pending_meeting_id(conn, user_id)
            if existing_meeting_id:
                return await _get_meeting_with_matched_user(conn, existing_meeting_id, user_id)

            if await _candidate_has_pending_meeting(conn, matched_user_id):
                return None

            meeting_id = await conn.fetchval(
                """
                INSERT INTO public.meetings(user_1_id, user_2_id, status, created_at, last_updated)
                VALUES($1, $2, 'new', now(), now())
                RETURNING id
                """,
                user_id,
                matched_user_id,
            )

            return await _get_meeting_with_matched_user(conn, int(meeting_id), user_id)


@app.get("/tma/meetings/{meeting_id}")
async def tma_get_meeting(meeting_id: int, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    user_id = tg_user.get("id")
    async with pool.acquire() as conn:
        result = await _get_meeting_with_matched_user(conn, meeting_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return result


@app.post("/tma/meetings/{meeting_id}/confirm")
async def tma_confirm_meeting(meeting_id: int, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            "SELECT user_1_id, user_2_id FROM public.meetings WHERE id=$1",
            meeting_id,
        )
        if not pair:
            raise HTTPException(status_code=404, detail="Meeting not found")
        await conn.execute(
            """
            UPDATE public.meetings
            SET status='met', last_updated=now()
            WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
              AND status = 'new'
            """,
            pair["user_1_id"],
            pair["user_2_id"],
        )
    return {"ok": True}


@app.post("/tma/meetings/{meeting_id}/decline")
async def tma_decline_meeting(meeting_id: int, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            "SELECT user_1_id, user_2_id FROM public.meetings WHERE id=$1",
            meeting_id,
        )
        if not pair:
            raise HTTPException(status_code=404, detail="Meeting not found")
        await conn.execute(
            """
            UPDATE public.meetings
            SET status='cancelled', last_updated=now()
            WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
              AND status = 'new'
            """,
            pair["user_1_id"],
            pair["user_2_id"],
        )
    return {"ok": True}


@app.post("/tma/meetings/{meeting_id}/already_know")
async def tma_already_know(meeting_id: int, tg_user: dict = Depends(_get_tma_user)):
    if not pool:
        raise HTTPException(status_code=503, detail="DB not ready")
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            "SELECT user_1_id, user_2_id FROM public.meetings WHERE id=$1",
            meeting_id,
        )
        if not pair:
            raise HTTPException(status_code=404, detail="Meeting not found")
        await conn.execute(
            """UPDATE public.meetings
               SET status='cancelled', already_known=true, last_updated=now()
               WHERE ((user_1_id = $1 AND user_2_id = $2) OR (user_1_id = $2 AND user_2_id = $1))
                 AND status = 'new'""",
            pair["user_1_id"],
            pair["user_2_id"],
        )
    return {"ok": True}
