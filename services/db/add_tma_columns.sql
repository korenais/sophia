-- TMA Phase 1: new profile fields and meeting statuses
-- Safe to run multiple times (idempotent)

-- Extended profile fields for TMA
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS offer TEXT,
  ADD COLUMN IF NOT EXISTS request_text TEXT;

-- Extended meeting statuses for TMA actions
-- 'already_known' = user indicated they already know this match
ALTER TABLE public.meetings
  ADD COLUMN IF NOT EXISTS declined_by INTEGER[],
  ADD COLUMN IF NOT EXISTS already_known BOOLEAN DEFAULT FALSE;

-- Track per-user meeting count for profile stats
-- (computed in API from meetings table, no column needed)

-- Thanks received count — indexed for fast leaderboard
CREATE INDEX IF NOT EXISTS idx_users_field_of_activity ON public.users(field_of_activity);
CREATE INDEX IF NOT EXISTS idx_users_intro_location    ON public.users(intro_location);
CREATE INDEX IF NOT EXISTS idx_users_intro_name        ON public.users(intro_name);
CREATE INDEX IF NOT EXISTS idx_meetings_user1          ON public.meetings(user_1_id);
CREATE INDEX IF NOT EXISTS idx_meetings_user2          ON public.meetings(user_2_id);

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('offer', 'request_text')
ORDER BY column_name;
