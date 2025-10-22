-- Migration: Change account_id, provider_id, and transaction_id from INTEGER to UUID
-- Created: 2025-10-22
-- Description: Simple migration to convert primary keys from integer to UUID

-- IMPORTANT: This will clear all existing data in accounts, providers, and transactions tables
-- Backup your data before running this migration if needed

BEGIN;

-- Step 1: Drop RLS policies that depend on these columns
DROP POLICY IF EXISTS "Users can view own accounts" ON accounts;
DROP POLICY IF EXISTS "Users can insert own accounts" ON accounts;
DROP POLICY IF EXISTS "Users can update own accounts" ON accounts;
DROP POLICY IF EXISTS "Users can delete own accounts" ON accounts;

DROP POLICY IF EXISTS "Users can view own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can insert own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can update own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can delete own transactions" ON transactions;

DROP POLICY IF EXISTS "Users can view own connections" ON connections;
DROP POLICY IF EXISTS "Users can insert own connections" ON connections;
DROP POLICY IF EXISTS "Users can update own connections" ON connections;
DROP POLICY IF EXISTS "Users can delete own connections" ON connections;

DROP POLICY IF EXISTS "Users can view providers" ON providers;

-- Step 2: Drop all foreign key constraints that reference these columns
ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_provider_id_fkey;
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_account_id_fkey;
ALTER TABLE connections DROP CONSTRAINT IF EXISTS connections_provider_id_fkey;

-- Step 2: Truncate tables (since we can't convert existing integer IDs to UUIDs meaningfully)
TRUNCATE TABLE transactions CASCADE;
TRUNCATE TABLE accounts CASCADE;
TRUNCATE TABLE connections CASCADE;
TRUNCATE TABLE providers CASCADE;

-- Step 3: Drop existing default values first
ALTER TABLE providers ALTER COLUMN provider_id DROP DEFAULT;
ALTER TABLE accounts ALTER COLUMN account_id DROP DEFAULT;
ALTER TABLE transactions ALTER COLUMN transaction_id DROP DEFAULT;
-- Only drop default for connections.provider_id if it exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'connections' AND column_name = 'provider_id'
  ) THEN
    ALTER TABLE connections ALTER COLUMN provider_id DROP DEFAULT;
  END IF;
END $$;

-- Step 4: Change column types to UUID

-- Providers table
ALTER TABLE providers
  ALTER COLUMN provider_id TYPE UUID USING gen_random_uuid();

ALTER TABLE providers
  ALTER COLUMN provider_id SET DEFAULT gen_random_uuid();

-- Accounts table
ALTER TABLE accounts
  ALTER COLUMN account_id TYPE UUID USING gen_random_uuid();

ALTER TABLE accounts
  ALTER COLUMN account_id SET DEFAULT gen_random_uuid();

-- Transactions table
ALTER TABLE transactions
  ALTER COLUMN transaction_id TYPE UUID USING gen_random_uuid();

ALTER TABLE transactions
  ALTER COLUMN transaction_id SET DEFAULT gen_random_uuid();

ALTER TABLE transactions
  ALTER COLUMN account_id TYPE UUID USING NULL;

-- Connections table (only if provider_id column exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'connections' AND column_name = 'provider_id'
  ) THEN
    ALTER TABLE connections ALTER COLUMN provider_id TYPE UUID USING NULL;
  END IF;
END $$;

-- Step 5: Recreate foreign key constraints

ALTER TABLE transactions
  ADD CONSTRAINT transactions_account_id_fkey
  FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE;

-- Recreate connections foreign key only if provider_id exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'connections' AND column_name = 'provider_id'
  ) THEN
    ALTER TABLE connections
      ADD CONSTRAINT connections_provider_id_fkey
      FOREIGN KEY (provider_id) REFERENCES providers(provider_id) ON DELETE SET NULL;
  END IF;
END $$;

-- Step 6: Add comments
COMMENT ON COLUMN providers.provider_id IS 'UUID primary key for provider';
COMMENT ON COLUMN accounts.account_id IS 'UUID primary key for account';
COMMENT ON COLUMN transactions.transaction_id IS 'UUID primary key for transaction';
COMMENT ON COLUMN transactions.account_id IS 'Foreign key reference to accounts table';

-- Step 7: Recreate RLS policies

-- Accounts policies
CREATE POLICY "Users can view own accounts" ON accounts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own accounts" ON accounts
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own accounts" ON accounts
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own accounts" ON accounts
  FOR DELETE USING (auth.uid() = user_id);

-- Transactions policies (check ownership through accounts table)
CREATE POLICY "Users can view own transactions" ON transactions
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM accounts
      WHERE accounts.account_id = transactions.account_id
      AND accounts.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own transactions" ON transactions
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM accounts
      WHERE accounts.account_id = transactions.account_id
      AND accounts.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update own transactions" ON transactions
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM accounts
      WHERE accounts.account_id = transactions.account_id
      AND accounts.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own transactions" ON transactions
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM accounts
      WHERE accounts.account_id = transactions.account_id
      AND accounts.user_id = auth.uid()
    )
  );

-- Connections policies
CREATE POLICY "Users can view own connections" ON connections
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own connections" ON connections
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own connections" ON connections
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own connections" ON connections
  FOR DELETE USING (auth.uid() = user_id);

-- Providers policies (read-only for all authenticated users)
CREATE POLICY "Users can view providers" ON providers
  FOR SELECT USING (auth.role() = 'authenticated');

COMMIT;
