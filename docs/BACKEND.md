# Backend Technical Reference
# Baltic Business Club — Services Documentation

**Last updated:** April 2026  
**Covers:** `services/bot/`, `services/api/`, `services/db/`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Telegram Bot](#2-telegram-bot)
3. [REST API](#3-rest-api)
4. [Database](#4-database)
5. [Shared Concerns](#5-shared-concerns)

---

## 1. System Overview

Three backend processes communicate through a shared PostgreSQL database. The bot and the API run as separate Docker containers and never call each other directly.

```
┌─────────────────────────────────────────┐
│              PostgreSQL 15              │
│           (shared state store)          │
└────────────┬──────────────┬─────────────┘
             │              │
    ┌────────┴──┐      ┌────┴──────────┐
    │  Bot      │      │  FastAPI API  │
    │ (aiogram) │      │  port 8055    │
    └───────────┘      └──────┬────────┘
    Telegram polling          │
    Scheduled jobs      ┌─────┴──────┐  ┌────────────────┐
    Push notifications  │   Admin    │  │   TMA          │
                        │  (React)   │  │  (React)       │
                        │  port 8081 │  │  port 8082     │
                        └────────────┘  └────────────────┘
```

**No internal HTTP calls between bot and API.** All coordination happens through the DB. The API's `/api/notifications/{id}/send` endpoint is the only exception — it uses the Telegram Bot API directly via `httpx`.

---

## 2. Telegram Bot

**Entry point:** `services/bot/main.py`  
**Framework:** aiogram 3.13  
**Runtime:** async Python 3, long-polling  
**Key dependencies:** asyncpg, openai, aiohttp, Pillow, numpy

### 2.1 Startup sequence

```
main() →
  create_db_pool()
  create Bot + Dispatcher
  setup_bot_commands()        ← sets menu per chat type (private / group)
  init_throttling()
  init_match_system()         ← MatchSystem singleton
  init_followup_system()      ← MeetingFollowupSystem singleton
  init_username_cache()       ← UsernameCache singleton
  init_scheduler()            ← JobScheduler + registers all jobs
  init_bug_reporting()
  check_critical_configuration()  ← validates env vars, writes to feedbacks if broken
  init_feedback_notification()    ← admin DM on new feedback (requires FEEDBACK_USER_ID)
  register middleware
  register all handlers
  dp.start_polling()
```

### 2.2 User-facing commands

All commands respect `BOT_LANGUAGE` env var for Russian (`ru`) or English (`en`) responses. Commands listed in BotFather menu are scoped by chat type.

#### Private chat commands

| Command | Handler (line in main.py) | Description |
|---|---|---|
| `/start` | L454 | Entry point. If user has a profile → shows it and enters `ProfileStates.editing_profile`. If no profile → starts onboarding FSM. Also handles migration of frontend-created users (negative user_id → real Telegram ID). |
| `/edit_profile` | L1045 | Alias for `/start` when user has a profile — enters profile editing FSM. |
| `/view_profile` | L1049 | Shows own profile card (text + photo if available). |
| `/my_matches` | L1094 | Lists all meetings for the user. Each match shown with name, status (new/met/cancelled), and inline buttons for action. |
| `/browse` | L1504 | Shows paginated list of all active members as inline keyboard. Tap a name → view their profile card. |
| `/people` | L1610 | Alias for `/browse`. |
| `/report_an_issue` | L1053 | Starts feedback collection. Stores `type='issue'` in `feedbacks`. Notifies admin via DM if `FEEDBACK_USER_ID` is set. |
| `/suggest_a_feature` | L1071 | Same as above with `type='feature'`. |
| `/enable_matches` | L2132 | User re-enables match recommendations after having disabled them. Sets `matches_disabled=false`. |
| `/cancel` | L855 | Exits any active FSM state. Clears state. |
| `/help` | L891 | Shows command list and brief instructions. |

#### Admin-only commands (user ID `1541686636` hardcoded)

| Command | Description |
|---|---|
| `/generate_matches` | Manually trigger the matching algorithm. Generates pairs, creates meeting records, sends notifications to all matched users. |
| `/admin_disable_matches` | Disable matching for a specific user by ID. |
| `/admin_enable_matches` | Re-enable matching for a specific user by ID. |
| `/say` | Broadcast a message to all users or a specified user. |
| `/scheduler_status` | Show all scheduled jobs, their last/next run times, and intervals. |
| `/confirm_match` | Manually confirm a meeting by ID. |
| `/check_birthdays` | Manually trigger birthday greeting check (only if `BIRTHDAYS=Yes`). |

#### Group chat commands

| Command | Description |
|---|---|
| `/thanks @username [message]` | Send thanks to another member. Stored in `thanks` table. Optional message appended. Posts confirmation to group. |
| `/stats` | Show requester's own thanks stats (sent / received). |
| `/top` | Leaderboard of top thanks receivers in the group. |

### 2.3 FSM conversation flows

All flows use aiogram's FSM with `MemoryStorage`. States are stored per user per chat.

#### OnboardingStates — new user registration

Triggered by `/start` when user has no profile. Sequential linear flow, each step validated by `InputValidator` from `validators.py`.

```
waiting_for_name
  → waiting_for_location        (geocoded via GEOCODING_API_KEY)
  → waiting_for_description     (min 10 chars)
  → waiting_for_linkedin        (optional, validated format)
  → waiting_for_hobbies_drivers (optional)
  → waiting_for_skills          (optional)
  → waiting_for_field_of_activity
  → waiting_for_birthday        (optional, inline calendar picker)
  → waiting_for_photo           (optional, Telegram photo message)
  → profile_confirmation        (shows full profile preview, confirm/edit)
  → [saved to DB, finishedonboarding=true, OpenAI embedding generated]
```

On confirmation: calls `set_user_onboarding_data()` which upserts all fields + `vector_description` (OpenAI `text-embedding-3-large` embedding of the description) to `users` table.

`partial_onboarding_confirmation`: used when user with incomplete profile goes through abbreviated re-onboarding.

#### ProfileStates — profile viewing and editing

```
viewing_profile   — displays profile card
editing_profile   — shows edit menu keyboard
editing_name      ┐
editing_location  │
editing_description│
editing_linkedin  │  → each field individually editable
editing_hobbies_drivers│  → updates DB, returns to editing_profile
editing_skills    │
editing_field_of_activity│
editing_birthday  │
editing_photo     ┘
```

Edit mode: `handle_*_edit_mode` handlers in `scenes.py`. After saving each field, re-vectorizes description if it changed.

#### MyMatchesStates

`viewing_matches` — user browsing their match list. Inline buttons on each match row.

#### BrowseStates

`browsing_users` — user browsing the member directory via inline keyboard. Back/close buttons.

### 2.4 Inline button callback handlers

| Callback prefix | Handler (line) | Action |
|---|---|---|
| `match_met_{meeting_id}` | L2543 | Sets `meetings.status='met'`. Sends confirmation to both parties. |
| `match_block_{meeting_id}_{user_id}` | L2630 | Inserts into `match_blocks`. Cancels meeting. |
| `match_disable_{meeting_id}` | L2699 | Sets `users.matches_disabled=true`. Updates button in original message to "Enable". |
| `match_enable_{meeting_id}` | L2795 | Sets `users.matches_disabled=false`. Updates button to "Disable". |
| `view_profile_{user_id}` | L2953 | Shows target user's profile card (used when TMA not configured). |
| `browse_user_{user_id}` | L3025 | Shows member profile from browse list. |
| `birthday_*` | L1824 | Handles birthday date picker interactions (inline calendar). |
| `menu_*` | L1829 | Handles edit profile menu navigation. |

### 2.5 Scheduled jobs

Powered by `JobScheduler` in `scheduler.py`. Checks job due-times every 10 seconds. All jobs are `async` functions called with `bot` and `db_pool`.

| Job name | Interval | Description |
|---|---|---|
| `generate_weekly_matches` | 168h (weekly) | Runs `MatchSystem.generate_and_create_matches()` + `notify_matches()`. Full automated matching cycle. |
| `process_meeting_followups` | 12h | Finds meetings in `new` status older than configured delay. Sends follow-up messages asking if meeting happened. |
| `send_scheduled_notifications` | ~10s | Polls `notifications` table for records with `status='scheduled'` and `scheduled_at <= now()`. Sends to recipients, updates `sent_count`/`failed_count`, sets `status='sent'`. |
| `cleanup_old_messages` | 24h | Purges old records from `bot_messages` table. |
| `cleanup_expired_cache` | 6h | Clears stale username cache entries. |
| `update_user_interaction_dates` | 1h | Updates `updated_at` for recently interacting users. |
| `check_birthday_greetings` | 24h | Checks `users.intro_birthday` for today's birthdays. Sends personalized greeting. Sets `last_birthday_greeting_sent`. Only runs if `BIRTHDAYS=Yes`. |
| `check_recently_updated_birthdays` | ~5s | Near-realtime check for recently-added birthdays that may be today. Only runs if `BIRTHDAYS=Yes`. |

### 2.6 Matching algorithm (`match_system.py`, `match_generation.py`)

```
1. get_matchable_users() — fetches users where:
     finishedonboarding = true
     state = 'ACTIVE'
     vector_description IS NOT NULL
     length(trim(intro_description)) >= 10
     matches_disabled IS NULL OR = false

2. Build n×n cosine similarity matrix from vector_description embeddings

3. Greedy pairing:
   - Sort all (i,j) pairs by similarity descending
   - Assign pair if:
     · Both users still unpaired in this round
     · similarity >= 0.3 (MIN_SIMILARITY_THRESHOLD)
     · No existing 'met' meeting within 6 months
     · No active match_block between them

4. create_meetings() — inserts meeting records (status='new')

5. notify_matches() → _notify_match_pair() → _send_match_notification()
   - Sends HTML-formatted notification to each user
   - Includes matched user's name, location, description, LinkedIn
   - Keyboard: [📱 Open in App (TMA)] + [✅ Met] + [🚫 Block] + [⛔ Disable]
   - Also sends matched user's photo as a second message if available
```

Embeddings use `text-embedding-3-large` (3072 dimensions). The `vector_description` column stores `double precision[]`.

### 2.7 Middleware stack

Applied in registration order. Each middleware can short-circuit the handler chain.

| Middleware | File | Effect |
|---|---|---|
| `NoBotsMiddleware` | `middleware.py` | Drops all messages from bot accounts. |
| `UpdateUserInteractionMiddleware` | `middleware.py` | Updates `users.updated_at` on every message. Caches username to `users.username` via `UsernameCache`. |
| `DMOnlyCommandsMiddleware` | `dm_only_middleware.py` | Rejects commands in `DM_ONLY_COMMANDS` env var when sent in groups. Sends user a DM prompt instead. |
| `BlockBotCommandsInSceneMiddleware` | `middleware.py` | When user is in an active FSM state, blocks `/commands` except `/cancel` and `/help`. Prevents scene corruption. |
| `GroupMembershipMiddleware` | `middleware.py` | Only active when `TELEGRAM_GROUP_ID` is set. Verifies user is a current member of the configured group before processing their messages. |

### 2.8 Module reference

| File | Role |
|---|---|
| `main.py` | Dispatcher setup, all handler registrations, startup/shutdown |
| `scenes.py` | All FSM handlers, message templates (EN + RU), `build_profile_text()`, keyboard builders |
| `db.py` | All asyncpg database functions — single source of truth for DB access |
| `models.py` | SQLAlchemy ORM models — schema reference only, not used for runtime queries |
| `match_system.py` | `MatchSystem` class — full matching pipeline |
| `match_generation.py` | `cosine_similarity()` pure utility |
| `vectorization.py` | OpenAI embedding calls (`text-embedding-3-large`). `create_default_vector()` returns zero vector if OpenAI unavailable |
| `scheduler.py` | `JobScheduler` + `ScheduledJob` — interval-based background jobs |
| `notifications.py` | `send_scheduled_notifications()` — broadcast delivery logic |
| `meeting_followup.py` | `MeetingFollowupSystem` — post-meeting check-in messages |
| `birthday_greetings.py` | Birthday detection and greeting delivery |
| `thanks.py` | `/thanks`, `/stats`, `/top` handlers and DB logic |
| `feedback_notification.py` | Admin DM ping on new feedback submission |
| `bug_reporting.py` | Writes automatic bug reports to `feedbacks` table |
| `throttling.py` | `send_message_throttled()` — rate-limited send wrapper |
| `middleware.py` | All aiogram middleware classes |
| `dm_only_middleware.py` | `DMOnlyCommandsMiddleware` |
| `username_cache.py` | `UsernameCache` — resolves and caches Telegram usernames |
| `validators.py` | `InputValidator` — validates all user inputs during onboarding |
| `command_config.py` | `get_commands_for_chat_type()` — returns correct BotCommand list per scope |
| `command_restrictions.py` | Command access control definitions |

### 2.9 Environment variables (bot)

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes | Bot token from BotFather |
| `OPENAI_API_KEY` | Yes | Used for `text-embedding-3-large` vectorization |
| `GEOCODING_API_KEY` | Yes | Location text → lat/long during onboarding |
| `DB_URL` | Yes | PostgreSQL connection string |
| `BOT_LANGUAGE` | Yes | `ru` or `en` — applies globally to all users |
| `TELEGRAM_GROUP_ID` | No | If set, enables `GroupMembershipMiddleware` |
| `THANKS_TOPIC_ID` | No | Thread ID for thanks-related commands in supergroups |
| `BIRTHDAY_TOPIC_ID` | No | Thread ID for birthday posts |
| `BIRTHDAYS` | No | `Yes` to enable birthday system |
| `DM_ONLY_COMMANDS` | No | Comma-separated commands restricted to private chat |
| `FEEDBACK_USER_ID` | No | Telegram user ID to notify on new feedback submissions |
| `TMA_URL` | No | HTTPS URL of TMA service. If set, match notifications include a WebApp button |

---

## 3. REST API

**Entry point:** `services/api/main.py`  
**Framework:** FastAPI 0.112 + uvicorn  
**Port:** 8055  
**Auth:** Two separate auth models — admin endpoints use no auth (protected by CORS + network), TMA endpoints use Telegram initData HMAC validation.

> **Note on auth:** The admin API has no token auth — it relies on CORS origin allowlist (`CORS_ALLOWED_ORIGINS`) and the assumption that port 8055 is not publicly accessible. For hardening, adding an API key header to admin endpoints is recommended before any public exposure.

### 3.1 Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}`. No DB check. |
| `GET` | `/api/health` | Same. Alias. |

### 3.2 Users (Admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/users` | List all users, ordered by `updated_at` desc, limit 100. Returns resolved photo URLs. |
| `GET` | `/api/users/{user_id}` | Single user. |
| `POST` | `/api/users` | Create user (admin-side onboarding). Validates `user_telegram_link` format. Auto-generates `vector_description` via OpenAI if `intro_description` provided. Assigns negative user_id if none given (temporary, replaced on `/start`). |
| `PUT` | `/api/users/{user_id}` | Update user fields. If `intro_description` changes, regenerates `vector_description`. Validates LinkedIn URL and Telegram link formats. |
| `DELETE` | `/api/users/{user_id}` | Deletes user and all related records (cascade). |
| `PUT` | `/api/users/{user_id}/notifications` | Toggle `notifications_enabled` for a user. |
| `GET` | `/api/users/{user_id}/groups` | List groups the user belongs to. |
| `POST` | `/api/users/{user_id}/groups` | Add user to groups (body: `{group_ids: [...]}`). |
| `DELETE` | `/api/users/{user_id}/groups/{group_id}` | Remove user from a group. |
| `POST` | `/api/users/check-message-availability` | Check if bot can send messages to a list of user IDs (validates `chat_id`, `notifications_enabled`, `state`). Used before sending broadcasts. |

**Photo handling in responses:**  
`process_user_data()` is applied to every user response. It converts `intro_image` values:
- Base64 → `data:image/jpeg;base64,...` data URL
- Telegram file ID (non-URL string) → resolved via `https://api.telegram.org/bot{TOKEN}/getFile`
- Already a URL → returned as-is

### 3.3 Meetings (Admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/meetings` | List last 100 meetings with user names joined in. |

### 3.4 Feedback (Admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/feedback` | List all feedback sorted by `created_at` desc. |
| `DELETE` | `/api/feedback/{feedback_id}` | Delete single feedback record. |
| `DELETE` | `/api/feedback` | Delete all feedback. |
| `DELETE` | `/api/feedback/type/{feedback_type}` | Delete all feedback of given type (`issue` or `feature`). |

### 3.5 Thanks (Admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/thanks/stats` | Thanks statistics per user (sent/received counts). |
| `GET` | `/api/thanks/top` | Top N receivers by thanks count (default 10). |
| `GET` | `/api/thanks/recent` | Most recent thanks entries. |

### 3.6 Validation utilities

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/validate-telegram-username` | Attempts to resolve a Telegram username via Bot API. Returns `user_id`, `first_name`, `is_valid`. Used by admin panel when creating users. |
| `POST` | `/api/validate-linkedin-profile` | Validates LinkedIn URL format and attempts to fetch profile metadata. |

### 3.7 Notifications (Admin)

Full CRUD for scheduled broadcasts.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/notifications` | List all notifications, sorted by `created_at` desc. |
| `GET` | `/api/notifications/{id}` | Single notification. |
| `POST` | `/api/notifications` | Create notification. Fields: `message_text`, `scheduled_at`, `recipient_type` (`all`/`user`/`group`/`user_group`), `recipient_ids[]`, `image_url`. |
| `PUT` | `/api/notifications/{id}` | Update notification (only `scheduled` status). |
| `DELETE` | `/api/notifications/{id}` | Delete notification. |
| `POST` | `/api/notifications/{id}/send` | **Immediately send** notification (bypasses scheduler). Iterates recipients, calls Telegram Bot API directly via httpx. Updates `sent_count`, `failed_count`, `status`. |
| `GET` | `/api/telegram-group-info` | Fetches group metadata from Telegram API (name, member count, type). |

### 3.8 User Groups (Admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/groups` | List all user groups. |
| `GET` | `/api/groups/{id}` | Single group with member list. |
| `POST` | `/api/groups` | Create group (name must be unique). |
| `PUT` | `/api/groups/{id}` | Rename group. |
| `DELETE` | `/api/groups/{id}` | Delete group and all memberships. |
| `GET` | `/api/groups/{id}/users` | List all users in a group. |
| `GET` | `/api/groups/{id}/status` | Check if Telegram bot can reach all users in the group (validates `chat_id`, `notifications_enabled`, `state` for each member). Returns `OK`/`NOT_OK` with a list of up to 3 problematic users. |

### 3.9 TMA endpoints

All require `X-Telegram-Init-Data` header. The initData is validated via HMAC-SHA256 using the bot token as key (`_validate_tma_init_data()`). Returns `401` if missing or invalid.

| Method | Path | Description |
|---|---|---|
| `GET` | `/tma/photo/{user_id}` | Photo proxy. Resolves Telegram file IDs to image bytes. Supports base64, direct URLs, and Telegram file IDs. `Cache-Control: public, max-age=86400`. |
| `GET` | `/tma/me` | Own profile with aggregated `thanks_received` and `meetings_completed` counts. |
| `PUT` | `/tma/me` | Update own profile fields (`intro_name`, `intro_location`, `intro_description`, `intro_linkedin`, `intro_hobbies_drivers`, `intro_skills`, `field_of_activity`, `offer`, `request_text`). |
| `GET` | `/tma/members` | All active members (`finishedonboarding=true`, `state='ACTIVE'`). Supports `?search=` (ILIKE on name/location/industry/skills/description). Sorted by `thanks_received` desc. |
| `GET` | `/tma/members/{user_id}` | Single member profile with stats. |
| `GET` | `/tma/matches/pending` | Most recent `new`-status meeting for the calling user, with matched user's full profile. Returns `null` if none. |
| `GET` | `/tma/meetings/{id}` | Meeting by ID with matched user profile. |
| `POST` | `/tma/meetings/{id}/confirm` | Sets `status='met'`. |
| `POST` | `/tma/meetings/{id}/decline` | Sets `status='cancelled'`. |
| `POST` | `/tma/meetings/{id}/already_know` | Sets `status='cancelled'`, `already_known=true`. |

### 3.10 Configuration validation

On startup, `_validate_configuration()` checks:
- `CORS_ALLOWED_ORIGINS` is explicitly set (warns if using default)
- `VITE_API_BASE_URL` is not a localhost URL when production origins are detected

Issues are written to the `feedbacks` table (deduped per 24h window) so operators see them in the admin panel.

---

## 4. Database

**Engine:** PostgreSQL 15  
**Schema:** `public`  
**Connection:** asyncpg connection pool (min 1, max 5 connections per service)

### 4.1 Schema

#### `users`
Primary entity. One row per Telegram user.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `bigint PK` | Telegram user ID. Admin-created users get negative IDs (temporary) until they run `/start`. |
| `state` | `text` | `'ACTIVE'` (default) or custom states. Only `'ACTIVE'` users are matchable. |
| `chat_id` | `bigint` | Telegram chat ID for DMs. Required to send notifications. |
| `language` | `text` | Stored but ignored at runtime — `BOT_LANGUAGE` env var overrides for all users. |
| `username` | `text` | Cached Telegram @username. Updated via `UsernameCache`. |
| `intro_name` | `text` | Display name set during onboarding. |
| `intro_location` | `text` | City/country as entered (free text). |
| `intro_description` | `text` | Bio/description. Minimum 10 chars to be matchable. |
| `intro_image` | `text` | Telegram file ID (or base64 for admin-uploaded). Resolved to URL at query time. |
| `intro_linkedin` | `text` | LinkedIn URL or handle. |
| `intro_hobbies_drivers` | `text` | Free text. |
| `intro_skills` | `text` | Free text, typically comma-separated. |
| `intro_birthday` | `date` | Optional. Used by birthday greeting system. |
| `field_of_activity` | `text` | Industry/niche. |
| `vector_description` | `double precision[]` | OpenAI `text-embedding-3-large` embedding (3072 dims). Null until onboarding completes. |
| `vector_location` | `text` | Location vector (stored as text, legacy). |
| `finishedonboarding` | `boolean` | `true` after onboarding FSM completes. Required for matching. |
| `user_telegram_link` | `varchar(255)` | Telegram username (without @). Used for DM links. |
| `notifications_enabled` | `boolean` | If `false`, notifications are skipped for this user. |
| `matches_disabled` | `boolean` | User opted out of the matching system. |
| `last_birthday_greeting_sent` | `date` | Prevents duplicate greetings in same year. |
| `offer` | `text` | *(Phase 1 addition)* "What I can help with" for TMA profile. |
| `request_text` | `text` | *(Phase 1 addition)* "What I'm looking for" for TMA profile. |
| `created_at` / `updated_at` | `timestamptz` | |

**Matchable criteria (enforced in `db.get_matchable_users()`):**
```sql
WHERE finishedonboarding = true
  AND state = 'ACTIVE'
  AND vector_description IS NOT NULL
  AND intro_description IS NOT NULL
  AND length(trim(intro_description)) >= 10
  AND (matches_disabled IS NULL OR matches_disabled = false)
```

#### `meetings`
One row per matched pair.

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial PK` | |
| `user_1_id` | `bigint FK → users` | |
| `user_2_id` | `bigint FK → users` | |
| `status` | `text` | `'new'` → `'met'` or `'cancelled'` |
| `call_successful` | `boolean` | Legacy field. |
| `sent_followup_message` | `boolean` | `true` after follow-up message sent. |
| `already_known` | `boolean` | *(Phase 1)* Set when user clicks "Уже знакомы" in TMA. |
| `created_at` | `timestamptz` | |
| `last_updated` | `timestamptz` | Updated on any status change. |

Re-match exclusion: pairs with a `met` meeting in the last 6 months are excluded from new matching.

#### `feedbacks`
Feedback and bug reports from users and the system.

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial PK` | |
| `user_id` | `bigint` | `0` for system-generated bug reports. |
| `type` | `text` | `'issue'` or `'feature'` (user-submitted), `'bug'` (system). |
| `text` | `text` | Free-form content. |
| `created_at` | `timestamptz` | |

#### `thanks`
Peer recognition events. No FK constraints (usernames used, not IDs).

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial PK` | |
| `sender_user_id` | `bigint` | Telegram ID of sender. |
| `receiver_username` | `text` | @username of recipient. |
| `sender_username` | `text` | @username of sender. |
| `created_at` | `timestamptz` | |

Note: joining thanks to `users` requires matching `users.username` to `thanks.receiver_username`. The TMA queries use `to_user_id` alias conceptually but the actual column is `receiver_username`.

#### `notifications`
Scheduled and sent broadcast messages.

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial PK` | |
| `message_text` | `text` | HTML-formatted message body. |
| `scheduled_at` | `timestamptz` | When to send. |
| `sent_at` | `timestamptz` | When actually sent. |
| `status` | `text` | `'scheduled'` → `'sent'` or `'cancelled'` |
| `recipient_type` | `text` | `'all'`, `'user'`, `'group'`, `'user_group'` |
| `recipient_ids` | `bigint[]` | Array of user IDs (for `user`/`group`/`user_group` types). |
| `image_url` | `text` | Optional banner image URL. |
| `sent_count` | `int` | Successful deliveries. |
| `failed_count` | `int` | Failed deliveries. |
| `error_message` | `text` | Last error if any. |

#### `user_groups` / `user_group_memberships`
Named groups for targeted notifications. Many-to-many `users ↔ user_groups`.

#### `match_blocks`
Unidirectional block. A entry `(user_id=A, blocked_user_id=B)` means A has blocked B. The matching algorithm checks both directions: a pair is excluded if either direction has a block.

#### `bot_messages`
Audit log of bot messages. Cleaned periodically by scheduler.

### 4.2 Migrations

No migration framework. All migrations are plain `.sql` files in `services/db/`. Applied manually via `docker exec` or by `deploy_production.sh`.

| File | Purpose |
|---|---|
| `init.sql` | Full initial schema. Run once on empty DB. |
| `migrate_to_latest.sql` | Comprehensive catch-up migration for v1 → current. Safe to re-run (all `IF NOT EXISTS`). |
| `migrate_production_latest.sql` | Latest production migration bundle. |
| `add_tma_columns.sql` | Phase 1: adds `users.offer`, `users.request_text`, `meetings.already_known`. |
| `add_birthday_greeting_tracking.sql` | Adds `last_birthday_greeting_sent` column. |
| `add_user_groups.sql` | Adds `user_groups` and `user_group_memberships` tables. |
| `add_match_blocks.sql` | Adds `match_blocks` table. |
| `add_notifications_system.sql` | Adds `notifications` table. |
| `verify_schema.sql` | Read-only verification — lists all tables/columns. Run after migrations to confirm. |

**Running a migration:**
```bash
docker exec -i <db-container-name> psql -U postgres -d postgres < services/db/<migration>.sql
```

### 4.3 Indexes

Key indexes for query performance:

```sql
-- Matching eligibility scan
idx_users_finished_active         ON users(finishedonboarding, state)

-- Notification delivery
idx_users_notifications_enabled   ON users(notifications_enabled)

-- Birthday system
idx_users_last_birthday_greeting  ON users(last_birthday_greeting_sent)

-- Meeting lookups
idx_meetings_users                ON meetings(user_1_id, user_2_id)
idx_meetings_status               ON meetings(status)

-- Notification scheduling
idx_notifications_scheduled_at    ON notifications(scheduled_at) WHERE status='scheduled'

-- Match blocks
idx_match_blocks_pair             ON match_blocks(user_id, blocked_user_id)

-- TMA search (Phase 1 additions)
idx_users_intro_name              ON users(intro_name)
idx_users_intro_location          ON users(intro_location)
idx_users_field_of_activity       ON users(field_of_activity)
```

---

## 5. Shared Concerns

### 5.1 Image storage

Profile photos are stored as Telegram file IDs (strings like `AgACAgIAAxk...`) in `users.intro_image`. At display time:

- **Bot:** Downloads and sends via `BufferedInputFile` using the file ID directly.
- **Admin API / TMA API:** `process_user_data()` calls `get_telegram_image_url()` which resolves file ID → `https://api.telegram.org/file/bot{TOKEN}/{path}`.
- **TMA photo proxy** (`GET /tma/photo/{user_id}`): Streams image bytes directly, adds 24h cache header. Falls back gracefully if file ID is invalid.

Admin-uploaded images (via the admin panel create/edit form) may be stored as base64 strings. `is_base64_image()` detects this case and converts to a data URL.

### 5.2 Language handling

`BOT_LANGUAGE` env var is the single source of truth. The `db.get_user_language()` function **ignores** the `users.language` DB column and returns the env var value for all users. This means the language cannot be changed per-user — it is a global club setting.

### 5.3 Throttling

`throttling.py` wraps `bot.send_message()` to rate-limit outbound messages. Used by the match notification system and anywhere bulk messages are sent to prevent hitting Telegram API limits.

### 5.4 Username cache

`username_cache.py` maintains a TTL cache of Telegram user ID → username mappings. Refreshed when a user sends a message. Used by the thanks system (which operates on @usernames) to resolve display names for notifications.

### 5.5 Configuration self-healing

On startup, `check_critical_configuration()` (bot) and `_validate_configuration()` (API) both write detected issues to the `feedbacks` table with `user_id=0`. This means misconfiguration is visible in the admin panel's Feedback tab without requiring server log access.
