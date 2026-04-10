# Product Requirements Document
# Baltic Business Club — Platform Roadmap

**Product:** Sophia → BBC Mini App  
**Organization:** Baltic Business Club  
**Document status:** Living document  
**Last updated:** April 2026

---

## 1. Product Vision

Baltic Business Club is a private professional community operating across Estonia, UAE, Kazakhstan, and other geographies. The platform's mission is to turn club membership into active, measurable value: connections made, problems solved, deals closed.

### The shift: from bot-as-interface to app-as-home

The original Sophia bot proved the core value (automated matching works, the Thanks system creates recognition culture). The constraint was UX: FSM-based Telegram chat is a dead end for browsing, discovery, and rich interaction. Members forget commands, can't explore freely, and can't get a sense of the community they're part of.

The Telegram Mini App (TMA) replaces the user-facing interface while keeping the bot as the notification and push layer. The bot never goes away — Telegram does not allow Mini Apps to initiate pushes without a bot. The architecture is:

- **Bot** → notifications, match delivery, commands for power users
- **TMA** → primary user interface (browse, profile, match actions, requests, events)
- **FastAPI** → shared backend for both
- **Admin panel** → operator tooling (separate React app, unchanged)

---

## 2. What Was Built Before Phase 1

### Infrastructure (self-hosted, Docker Compose)

The platform was deployed before TMA work began. All services run on a single production server (`ssh -p 22124 aanisimov@2.57.222.34`, public at `vm18.digisoov.ee`) via Docker Compose.

| Service | Stack | Port |
|---|---|---|
| Bot | Python 3, aiogram 3 | — (Telegram polling) |
| API | Python 3, FastAPI | 8055 |
| Admin frontend | React 18, MUI, Vite | 8081 |
| Database | PostgreSQL 15 | 5433 (local) |

### Bot capabilities (fully operational)

**Onboarding flow (FSM)**  
Collects: name, location, bio/description, LinkedIn, skills, field of activity, hobbies & drivers, birthday, profile photo. Stores to `users` table with `finishedonboarding=true` on completion.

**AI Matching (Random Coffee)**  
Generates user pairs using OpenAI `text-embedding-3-large` embeddings on profile descriptions. Cosine similarity matrix, greedy pairing algorithm, minimum threshold 0.3. Excludes pairs with recent `met` meetings (6-month window) and active blocks. Sends match notification with inline buttons (met / block / disable).

**Thanks system**  
`/thanks @username` in group chat. Stores in `thanks` table with sender/receiver. `/stats` and `/top` show leaderboard. Used for club culture and recognition.

**Birthday greetings**  
Optional feature (`BIRTHDAYS=Yes`). Sends personalized birthday messages to members on their birthday. Posts to a designated Telegram topic.

**Scheduled notifications**  
Admin-created broadcasts stored in `notifications` table, delivered via bot on schedule. Supports `all` / specific users / user groups as recipients. Optional banner image.

**Feedback & bug reporting**  
`/report_an_issue` and `/suggest_a_feature` commands. Stored in `feedbacks` table. Admin panel shows all feedback.

**Meeting follow-up**  
After a match meeting, bot sends a follow-up message asking if the meeting happened. Updates `meetings.status` to `met` on confirmation.

**Middleware stack**  
- `PrivateChatOnlyMiddleware` — blocks group usage of private commands
- `GroupMembershipMiddleware` — verifies user is an active group member
- `UpdateUserInteractionMiddleware` — tracks last activity
- `BlockBotCommandsInSceneMiddleware` — prevents command interference during FSM flows
- `DMOnlyCommandsMiddleware` — configurable via `DM_ONLY_COMMANDS` env var

### Admin panel capabilities

React SPA at port 8081, password-protected. Tabs:
- **People** — full user table, edit any profile, view status
- **Matches** — all meetings, status, participants
- **Notifications** — create/schedule/cancel broadcasts
- **Feedback** — all submitted issues and feature requests
- **Thanks** — thanks log

### Database schema (pre-Phase 1)

```
users              — profiles, vectors, onboarding state, match settings
meetings           — user pairs, status (new/met/cancelled), followup tracking
feedbacks          — issues and feature requests
thanks             — peer recognition log
notifications      — scheduled broadcasts
user_groups        — named groups for targeted notifications
user_group_memberships — many-to-many users ↔ groups
match_blocks       — bilateral block pairs
bot_messages       — message log
```

---

## 3. Phase 1 — TMA Foundation

**Status:** Complete  
**Scope:** Replace bot's user-facing UX with a Mini App for the core networking loop.

### 3.1 What was built

#### New service: `services/tma/`

A Vite + React 18 + TypeScript Mini App, served via nginx at port 8082.

**Tech stack:**
- React 18, React Router v6
- `@twa-dev/sdk` — Telegram Web Apps SDK
- Tailwind CSS
- Fonts: Cormorant Garamond (display) + Jost (body)

**Design system — Baltic Business Club branding:**

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#1A1C24` | Page background (matches BBC logo dark) |
| `--surface` | `#22252F` | Card backgrounds |
| `--raised` | `#2A2E3A` | Elevated surfaces, info blocks |
| `--border` | `#363B4F` | Dividers, card outlines |
| `--gold` | `#C9A84C` | Primary accent (from BBC crest ornaments) |
| `--gold-light` | `#E3C96A` | Hover, shimmer |
| `--cream` | `#EDE9E3` | Primary text (warm white) |
| `--muted` | `#7A8099` | Secondary text |

Gold shimmer animation on headings. Staggered card entrance animations. Haptic feedback on all interactions. Light/Dark mode follows Telegram system setting automatically.

#### Screens

**People directory** (`/people`)  
- Full member list with avatar, name, industry, location, skills preview
- Real-time search (name, location, industry, skills, description)
- Country cloud — tap a country to filter, shows member counts
- Sorted by Thanks received (most active members surface first)
- Staggered fade-up animations per card

**Member profile** (`/people/:userId`)  
- Large avatar with gold ring + animated glow
- Name (Cormorant Garamond display), industry (gold), location
- Thanks and meetings stats badges
- Sections: About, "What I can help with" (offer), "What I'm looking for" (request_text), Skills chips, Interests, LinkedIn
- "Write on Telegram" primary CTA (gold button, opens Telegram DM)
- LinkedIn secondary CTA

**My Profile** (`/profile`)  
- Own profile view with edit button
- Stats: Thanks received, meetings completed
- Same section structure as member view
- Empty-state prompts for unfilled sections (tap to edit)

**Edit Profile** (`/profile/edit`)  
- Form fields: Name, Industry/Niche, City/Country, Bio, Offer, Request, Skills, LinkedIn, Hobbies
- Multi-line textareas for long-form fields
- Gold save button with loading/success states and haptic feedback

**Match reveal** (`/match/:meetingId`) — the core Phase 1 flow  
- Full-screen profile reveal of matched user
- Decorative concentric gold ring animation around avatar
- "AI-Консьерж · Новый матч" pill indicator
- All profile info displayed (offer, skills, description)
- Three action buttons:
  - ✓ Встретились (confirm meeting → status `met`)
  - ~ Уже знакомы (already know → status `cancelled` + `already_known=true`)
  - ✕ Пропустить (decline → status `cancelled`)
- "Write in Telegram" primary CTA
- Done confirmation screen per action taken

**Bottom navigation**  
- 2 active tabs: People, Я (Profile)
- 3 inactive/coming-soon tabs: Ивенты, Запросы, Сервисы (visually dimmed, signals roadmap)
- Gold indicator line on active tab
- Haptic feedback on tab switch

**Loading screen**  
- Animated BBC shield SVG (stroke draw animation)
- "Baltic Business Club" in gold Cormorant Garamond

#### Authentication

Every TMA request includes the `X-Telegram-Init-Data` header (Telegram's signed HMAC-SHA256 payload). The FastAPI backend validates it in `_validate_tma_init_data()` using the bot token as the key. No separate login, no passwords — Telegram identity is authoritative.

#### New API endpoints (`/tma/*`)

All require valid `X-Telegram-Init-Data`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tma/me` | Own profile with thanks + meetings count |
| `PUT` | `/tma/me` | Update own profile fields |
| `GET` | `/tma/members` | All active members (`?search=` supported) |
| `GET` | `/tma/members/{user_id}` | Single member profile |
| `GET` | `/tma/photo/{user_id}` | Photo proxy — resolves Telegram file IDs to image bytes, cached 24h |
| `GET` | `/tma/matches/pending` | Most recent `new` meeting for current user |
| `GET` | `/tma/meetings/{id}` | Meeting + matched user profile |
| `POST` | `/tma/meetings/{id}/confirm` | Sets status → `met` |
| `POST` | `/tma/meetings/{id}/decline` | Sets status → `cancelled` |
| `POST` | `/tma/meetings/{id}/already_know` | Sets status → `cancelled` + `already_known=true` |

#### Bot changes

Match notification now includes a `📱 Открыть в приложении` button using `WebAppInfo` (aiogram's TMA opener). Activated by setting `TMA_URL` env var. Falls back to callback-button behavior if `TMA_URL` is not set (backwards compatible).

#### DB migration (`services/db/add_tma_columns.sql`)

```sql
users.offer          TEXT   -- "What I can help with" (Чем могу помочь)
users.request_text   TEXT   -- "What I'm looking for" (Что ищу)
meetings.already_known BOOLEAN DEFAULT FALSE
```

#### New env vars

| Variable | Service | Description |
|---|---|---|
| `TMA_URL` | bot, docker-compose | HTTPS URL of the TMA (e.g. `https://vm18.digisoov.ee:8082`). Required for TMA buttons in match notifications. |
| `TMA_PORT` | docker-compose | Host port for TMA container. Default: `8082`. |

### 3.2 Deployment

```bash
# Run DB migration on production
docker exec -i <db-container> psql -U postgres -d postgres < services/db/add_tma_columns.sql

# Add to infra/.env
TMA_URL=https://vm18.digisoov.ee:8082
TMA_PORT=8082

# Rebuild affected services
cd infra && docker-compose up --build tma api bot
```

**BotFather setup (one-time):**  
1. `/newapp` → set app URL to `https://vm18.digisoov.ee:8082`
2. This creates the persistent app button in the bot chat

### 3.3 What Phase 1 does NOT include

- Events / calendar (Phase 2)
- Request exchange / Биржа запросов (Phase 2)
- Club Coins / gamification (Phase 2)
- Services / Partners (Phase 3)
- Family block in profile (deferred — not core to networking value)
- QR code / digital business card (deferred)
- Segmented push notifications from TMA (Phase 3)
- MAU/DAU analytics in admin panel (Phase 3)

---

## 4. Phase 2 — Network Activity Layer

**Status:** Planned  
**Goal:** Add the active networking features that create daily engagement: events and requests.

### 4.1 Events (Fienta RSS integration)

**Source:** `fienta.com/et/o/397` RSS feed  
**New screen:** `📅 Ивенты` tab (currently dimmed in nav)

Features:
- Auto-import events from Fienta RSS on a schedule (every 15–30 min)
- Featured next event with large banner (16:9), date/time/location/speaker
- Event calendar list below the featured event
- "Я пойду" (I'll attend) button — stores RSVP in new `event_attendees` table
- Attendee counter + avatar strip of who's going
- "Предложить тему / стать спикером" form → stores to `feedbacks` or new `event_proposals` table
- Bot notification when a new event is published

**New tables:**
```sql
events (id, fienta_id, title, description, starts_at, location, banner_url, created_at)
event_attendees (event_id, user_id, created_at)
```

**New API endpoints:**
- `GET /tma/events` — upcoming events with attendee counts
- `GET /tma/events/{id}` — event detail + attendees
- `POST /tma/events/{id}/attend` — RSVP
- `DELETE /tma/events/{id}/attend` — cancel RSVP
- `POST /tma/events/propose` — suggest topic/speaker

### 4.2 Request Exchange (Биржа запросов)

**New screen:** `🔍 Запросы` tab (currently dimmed in nav)

A time-limited marketplace of member needs. Members post what they're looking for; others respond.

**Mechanics:**
- Request lives for 10 calendar days from creation
- On day 9: bot sends "Is your request still relevant?" with [Extend 10 days] / [Delete] buttons
- If no active request for 14+ days: bot sends "How can the club help you today?"
- Tags: freeform hashtags per request (e.g. `#маркетинг #оаэ #юрист`)
- Like / "Могу помочь" (opens Telegram DM with requester)

**Feed views:**
- All requests (sorted by recency)
- My requests
- Filter by tag

**New table:**
```sql
requests (
  id, user_id, text, tags TEXT[],
  status TEXT DEFAULT 'active',  -- active | extended | resolved | expired
  expires_at TIMESTAMPTZ,
  created_at, updated_at
)
```

**New API endpoints:**
- `GET /tma/requests` — active requests (`?tag=`, `?mine=true`)
- `POST /tma/requests` — create request
- `PUT /tma/requests/{id}` — update/extend
- `DELETE /tma/requests/{id}` — delete
- `POST /tma/requests/{id}/resolve` — mark resolved

**Bot changes:**
- Scheduler job: check requests expiring tomorrow, send day-9 reminder
- Scheduler job: check users with no request for 14 days, send engagement push

### 4.3 Club Coins (Gamification)

Lightweight reputation currency that rewards confirmed meetings.

**Mechanics:**
- Earn coins when both sides confirm a meeting (`meetings.status = 'met'`)
- Coins visible on Profile screen
- Used in Phase 3 to unlock partner offers

**New table:**
```sql
coin_transactions (id, user_id, amount, reason TEXT, meeting_id, created_at)
```

Computed balance: `SELECT SUM(amount) FROM coin_transactions WHERE user_id=$1`

---

## 5. Phase 3 — Services, Analytics, Polish

**Status:** Planned  
**Goal:** Monetization layer (partner offers), deep analytics for operators, and quality-of-life features.

### 5.1 Services / Partners tab

**New screen:** `🎁 Сервисы` tab

Two sub-sections toggled by a switcher:

**Партнеры (Partner offers):**
- Partner cards: logo, name, description, discount/offer
- Price: free (for residents) or Club Coins cost
- "Получить промокод" — shows promo code (free) or deducts coins + shows code
- "Предложить партнёра" form

**Знания (Knowledge library):**
- YouTube video grid, categorized
- Managed by admin (URLs stored in new `knowledge_items` table)

**New tables:**
```sql
partners (id, name, logo_url, description, offer_text, promo_code, coin_cost, is_active)
knowledge_items (id, title, youtube_url, category, created_at)
```

### 5.2 Admin panel enhancements (Sophia Admin)

New analytics tabs in the existing React admin panel:

**Matching funnel:**
- Total pairs created
- Viewed profile in TMA (requires frontend event tracking)
- Confirmed meeting (both sides)
- Declined / already known / no response
- Decline reason breakdown

**Request activity:**
- New requests per day/week
- % resolved
- Top tags / most-requested topics

**App metrics:**
- DAU/MAU (unique TMA sessions per day/month, requires session tracking)
- Thanks leaderboard
- Members with no activity in 30+ days (churn risk)

### 5.3 Profile enhancements

**QR code / Digital business card:**
- "Твой QR-код (Визитка)" button on profile
- QR encodes the user's TMA deep link: `tma_url/people/{user_id}`
- Generated client-side (no backend needed)

**Profile tabs (Business / Family / Blog):**
- Business tab: current profile fields
- Family tab: marital status, children, shared interests — privacy controls (show to: all / members only / admins only)
- Blog tab: freeform text or link to external blog

### 5.4 Segmented push notifications

Extend the existing `notifications` table to support TMA-aware filtering:

- Filter by country, industry, revenue range, group membership
- Notification includes "Open in App" button with deep link to relevant TMA screen

### 5.5 Onboarding in TMA

Move the onboarding flow from bot FSM into the TMA:
- First-time user sees a step-by-step form in the app
- Replaces the awkward chat-based Q&A
- Bot still triggers the onboarding link (`/start` → sends TMA button)

---

## 6. Architecture Reference

### Service map (post-Phase 1)

```
Telegram user
    │
    ├── Bot (aiogram 3, Python)  ←──── PostgreSQL 15
    │     · commands (/thanks, /stats, etc.)        │
    │     · match notifications with TMA button      │
    │     · scheduled jobs (matching, birthdays,     │
    │       follow-ups, request reminders)           │
    │                                                │
    └── TMA (React, port 8082)  ←── FastAPI (port 8055)
          · People directory                  · /tma/* endpoints (TMA auth)
          · Own profile view/edit             · /api/* endpoints (admin auth)
          · Match reveal + actions            · photo proxy
          · [Events — Phase 2]                · HMAC validation
          · [Requests — Phase 2]
          · [Services — Phase 3]

Admin operator
    └── Admin panel (React, port 8081) ←── FastAPI /api/* (password auth)
```

### Auth model

| Client | Auth method |
|---|---|
| TMA | `X-Telegram-Init-Data` header — HMAC-SHA256 validated server-side using bot token |
| Admin panel | Password (`FRONTEND_PASSWD` env var) stored in session |
| Bot→API | Internal Docker network — no auth (same compose network) |

### Key design decisions

**Bot is not replaced — it's the notification layer.**  
Telegram Mini Apps cannot push to users without a bot. Every user notification (match, request reminder, event, birthday) goes through the bot.

**Language is global, not per-user.**  
`BOT_LANGUAGE` env var controls all bot messages. The `language` column in `users` is ignored at runtime. The TMA is Russian-first based on the community.

**Matching eligibility criteria (unchanged from pre-Phase 1):**  
`finishedonboarding=true` AND `state='ACTIVE'` AND `vector_description IS NOT NULL` AND `length(trim(intro_description)) >= 10` AND `matches_disabled != true`

**No ORM at query time.**  
SQLAlchemy models in `models.py` are for schema reference only. All runtime DB access uses raw `asyncpg` queries for performance and explicit control.

---

## 7. Source documents

- `docs/tma-prototype-wireframes.pdf` — UI wireframes for all 6 TMA screens
- `docs/tma-technical-spec.pdf` — Original TZ (technical specification) document
- `CLAUDE.md` — Developer guide for Claude Code and human developers

---

## 8. Open questions / decisions needed

| # | Question | Owner |
|---|---|---|
| 1 | TMA URL — will `vm18.digisoov.ee:8082` serve over HTTPS? TMA requires HTTPS. May need nginx reverse proxy at port 443. | Infra |
| 2 | BotFather app name — what should the Mini App be called? This determines the `t.me/botname/appname` URL. | Product |
| 3 | Onboarding migration — do we want to move onboarding to TMA in Phase 2 or keep bot FSM? | Product |
| 4 | Family block — should it be included in Phase 2 or remain deferred? The TZ includes it, but it adds privacy complexity. | Product |
| 5 | Fienta RSS — does the club own the `fienta.com/et/o/397` organizer account? Need API/RSS access confirmed. | Product |
| 6 | Club Coins exchange rate — how many coins per confirmed meeting? Any other earn mechanisms? | Product |
| 7 | Request moderation — are requests published immediately or require admin approval? | Product |
