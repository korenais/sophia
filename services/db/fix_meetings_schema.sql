-- Fix meetings table schema to ensure sent_followup_message column exists
ALTER TABLE public.meetings 
ADD COLUMN IF NOT EXISTS sent_followup_message boolean DEFAULT false;

-- Update any existing records to have the default value
UPDATE public.meetings 
SET sent_followup_message = false 
WHERE sent_followup_message IS NULL;


