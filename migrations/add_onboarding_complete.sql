-- Migration: Add onboarding_complete column to profiles table
-- Created: 2025-10-22
-- Description: Track whether user has completed the bank onboarding process

-- Add onboarding_complete column to profiles table
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN DEFAULT FALSE;

-- Add comment to the column
COMMENT ON COLUMN profiles.onboarding_complete IS 'Indicates whether the user has completed the bank account onboarding process';

-- Update existing users to have onboarding_complete = false by default
UPDATE profiles
SET onboarding_complete = FALSE
WHERE onboarding_complete IS NULL;

-- Optional: Set onboarding_complete to true for users who already have accounts
-- This prevents existing users from being forced through onboarding again
UPDATE profiles p
SET onboarding_complete = TRUE
WHERE EXISTS (
    SELECT 1
    FROM accounts a
    WHERE a.user_id = p.id
);

-- Create index for faster queries on onboarding status
CREATE INDEX IF NOT EXISTS idx_profiles_onboarding_complete
ON profiles(onboarding_complete);
