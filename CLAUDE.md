# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Sophia is a **Telegram-based professional networking platform** that matches community members for 1-on-1 meetups. Users onboard via the bot, get matched automatically based on profile similarity (OpenAI embeddings + cosine similarity), and the admin dashboard lets operators manage users, matches, and notifications.

Production server: `ssh -p 22124 aanisimov@2.57.222.34` (also at `vm18.digisoov.ee`)

---

## Running locally

All services are orchestrated from `infra/`:

```bash
cd infra
cp env.sample.txt .env   # then fill in TELEGRAM_TOKEN, OPENAI_API_KEY, GEOCODING_API_KEY
docker-compose up --build
```

Services:
- **Bot**: no exposed port (Telegram polling)
- **API**: `http://localhost:8055`
- **Frontend**: `http://localhost:8081`
- **DB**: `localhost:5433` (Postgres 15)

Frontend local dev (hot reload):
```bash
cd services/frontend
npm install
VITE_API_BASE_URL=http://localhost:8055 VITE_FRONTEND_PASSWD=frontend npm run dev
```

---

## Key environment variables (`infra/.env`)

| Variable | Purpose |
|---|---|
| `TELEGRAM_TOKEN` | Bot token from @BotFather |
| `OPENAI_API_KEY` | Used for user profile embeddings |
| `GEOCODING_API_KEY` | Location text → coordinates |
| `BOT_LANGUAGE` | `ru` or `en` — applies to ALL users (not per-user) |
| `BIRTHDAYS` | `Yes`/`No` — enables birthday greeting system |
| `TELEGRAM_GROUP_ID` | Group the bot operates in |
| `THANKS_TOPIC_ID` | Topic thread for `/thanks` commands |
| `DM_ONLY_COMMANDS` | Comma-separated commands restricted to DMs |
| `FRONTEND_PASSWD` | Admin dashboard password |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list; must be explicit (no `*`) |

---

## Architecture

### `services/bot/` — Python/aiogram 3

The bot is the core product. Key modules and their roles:

| File | Role |
|---|---|
| `main.py` | Entry point: wires up dispatcher, registers all handlers, starts polling |
| `scenes.py` | All FSM conversation flows (onboarding, profile edit, browse, my_matches) |
| `db.py` | All database access — raw `asyncpg` queries, no ORM at runtime |
| `models.py` | SQLAlchemy ORM models for schema reference only (not used for queries) |
| `match_system.py` | `MatchSystem` class — generates pairs via greedy cosine similarity, creates meetings |
| `match_generation.py` | Pure `cosine_similarity()` utility |
| `vectorization.py` | OpenAI `text-embedding-3-large` calls for profile descriptions |
| `scheduler.py` | `JobScheduler` — runs background jobs on hour-interval schedules |
| `notifications.py` | Sends scheduled broadcast notifications to users/groups |
| `middleware.py` | aiogram middleware: DM-only enforcement, group membership check, interaction tracking, bot-command blocking during FSM |
| `throttling.py` | Rate-limited `send_message_throttled()` wrapper |
| `thanks.py` | `/thanks` command — peer recognition system with stats/leaderboard |
| `birthday_greetings.py` | Birthday greeting scheduler (requires `BIRTHDAYS=Yes`) |
| `meeting_followup.py` | Follow-up messages after meetings to collect feedback |
| `bug_reporting.py` | In-bot bug/issue reporting to DB |
| `username_cache.py` | Caches Telegram usernames to avoid repeated API calls |
| `command_config.py` | Central command list and scope configuration |

**FSM state flow**: Users progress through `OnboardingStates` → profile stored in DB with `finishedonboarding=true`. Active users with valid `vector_description` and `intro_description ≥ 10 chars` are eligible for matching.

**Matching logic**: `MatchSystem._generate_user_pairs()` builds a cosine similarity matrix from OpenAI embeddings, then greedily pairs users with similarity ≥ 0.3. Pairs with a `met` meeting in the last 6 months or active blocks are excluded.

**Language**: `BOT_LANGUAGE` env var controls language for all users globally. `get_user_language()` in `db.py` ignores the DB `language` column and always reads the env var.

### `services/api/` — Python/FastAPI

Single-file service (`main.py`). Exposes REST endpoints consumed by the React admin dashboard. Uses `asyncpg` directly. Handles CORS via explicit origin list from `CORS_ALLOWED_ORIGINS`.

### `services/frontend/` — React/TypeScript (Vite + MUI)

Admin-only SPA. `src/` contains one table component per entity type. Auth is a simple password check via `AuthContext`. No routing library — single-page with tab navigation.

### `services/db/` — PostgreSQL migrations

No migration framework. Migrations are plain `.sql` files applied manually or via `deploy_production.sh`. The canonical current state is `init.sql` + `migrate_production_latest.sql`. `verify_schema.sql` can be run to confirm schema health.

**Important**: Migration files in `docker-entrypoint-initdb.d/` only run on first DB initialization (empty DB). For existing databases, run migrations manually:
```bash
docker exec -i <db-container> psql -U postgres -d postgres < services/db/migrate_production_latest.sql
```

---

## Deployment

```bash
# On the production server or locally targeting production:
./deploy_production.sh
```

The script: backs up DB → `docker-compose build` → `docker-compose up -d` → applies migrations → verifies schema.

Manual backup:
```bash
./backup_database_production.sh
```

Check running services:
```bash
cd infra && docker-compose ps
docker-compose -f infra/docker-compose.yml logs -f bot
```

---

## TMA (Telegram Mini App) — Phase 1

### New service: `services/tma/`
React + TypeScript + Vite app served at port 8082. Opened from bot match notifications via `WebAppInfo` button.

**Design system**: Dark charcoal `#1A1C24` + gold `#C9A84C` + Cormorant Garamond (display) + Jost (body). Matches Baltic Business Club branding.

**Screens**:
| Route | Screen |
|---|---|
| `/people` | Member directory with search + country cloud |
| `/people/:userId` | Member profile detail |
| `/profile` | My profile view |
| `/profile/edit` | Edit profile form |
| `/match/:meetingId` | Match reveal — opened via deep link from bot |

**Auth**: Every TMA API call includes `X-Telegram-Init-Data` header (Telegram's signed payload). Backend validates via HMAC-SHA256 with bot token in `_validate_tma_init_data()`.

**Deep link flow**: Bot sends match notification → "📱 Открыть в приложении" button with `web_app=WebAppInfo(url=TMA_URL/match/{meeting_id})` → TMA opens, shows matched profile, user confirms/declines/already_know.

**New API endpoints** (all require `X-Telegram-Init-Data`):
- `GET /tma/me`, `PUT /tma/me`
- `GET /tma/members`, `GET /tma/members/{user_id}`
- `GET /tma/photo/{user_id}` — proxies Telegram file IDs to image bytes
- `GET /tma/matches/pending`, `GET /tma/meetings/{id}`
- `POST /tma/meetings/{id}/confirm|decline|already_know`

**New DB columns** (run `services/db/add_tma_columns.sql`):
- `users.offer` — "чем могу помочь"
- `users.request_text` — "что ищу"
- `meetings.already_known` — flag for "already know this person"

**New env vars**: `TMA_URL` (bot), `TMA_PORT` (docker-compose, default 8082)

**TMA local dev**:
```bash
cd services/tma && npm install && npm run dev  # runs on :5174
```

## Database schema (key tables)

| Table | Key columns |
|---|---|
| `users` | `user_id` (Telegram ID), `finishedonboarding`, `state` (`ACTIVE`/etc), `vector_description` (float[]), `matches_disabled`, `intro_*` fields |
| `meetings` | `user_1_id`, `user_2_id`, `status` (`new`/`met`/`cancelled`), `sent_followup_message` |
| `feedbacks` | `user_id`, `type`, `text` |
| `notifications` | `recipient_type` (`all`/`user`/`group`/`user_group`), `recipient_ids`, `status` (`scheduled`/`sent`/`cancelled`) |
| `match_blocks` | `user_id`, `blocked_user_id` — bidirectional block pairs |
| `user_groups` | Named groups for targeted notifications |

Matchable user criteria (enforced in `db.py:get_matchable_users`):
- `finishedonboarding = true`
- `state = 'ACTIVE'`
- `vector_description IS NOT NULL`
- `length(trim(intro_description)) >= 10`
- `matches_disabled IS NULL OR matches_disabled = false`
