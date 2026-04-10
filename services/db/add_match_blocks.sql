-- Add matches_disabled column to users table
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS matches_disabled boolean DEFAULT false;

-- Create match_blocks table to store user-specific match blocks
CREATE TABLE IF NOT EXISTS public.match_blocks (
    id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    blocked_user_id bigint NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, blocked_user_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_match_blocks_user ON public.match_blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_blocked ON public.match_blocks(blocked_user_id);
CREATE INDEX IF NOT EXISTS idx_match_blocks_pair ON public.match_blocks(user_id, blocked_user_id);
