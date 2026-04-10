-- Add language column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS language text;

-- Set default value for existing rows
UPDATE users SET language = 'en' WHERE language IS NULL;

-- Set default value for the column
ALTER TABLE users ALTER COLUMN language SET DEFAULT 'en';
