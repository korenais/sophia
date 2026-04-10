-- Add user groups system
-- This migration creates tables for user groups and group memberships
-- Safe to run multiple times (idempotent)

-- Create user_groups table
CREATE TABLE IF NOT EXISTS user_groups (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create user_group_memberships junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS user_group_memberships (
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, group_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_group_memberships_user_id ON user_group_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_user_group_memberships_group_id ON user_group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_user_groups_name ON user_groups(name);

-- Add comment to tables
COMMENT ON TABLE user_groups IS 'User groups for organizing users (e.g., "IT Business", "Users from Latvia")';
COMMENT ON TABLE user_group_memberships IS 'Junction table linking users to groups (many-to-many relationship)';

-- Verify tables were created successfully
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_groups'
    ) THEN
        RAISE EXCEPTION 'user_groups table was not created successfully';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_group_memberships'
    ) THEN
        RAISE EXCEPTION 'user_group_memberships table was not created successfully';
    END IF;
    
    RAISE NOTICE 'User groups tables verified successfully';
END $$;

