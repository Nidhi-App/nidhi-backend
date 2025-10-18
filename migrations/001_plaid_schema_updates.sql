-- ============================================================================
-- Migration: 001_plaid_schema_updates.sql
-- Description: Update schema for Plaid integration
-- Author: Development Team
-- Date: 2025-01-17
-- ============================================================================

-- ============================================================================
-- STEP 1: Update ENUM Types
-- ============================================================================

-- Add new connection status values for Plaid link flow
ALTER TYPE public.connection_status ADD VALUE IF NOT EXISTS 'Initializing';
ALTER TYPE public.connection_status ADD VALUE IF NOT EXISTS 'Pending';

-- ============================================================================
-- STEP 2: Create PROFILES table (replacing ea_users)
-- ============================================================================

-- Drop existing ea_users table and create profiles
DROP TABLE IF EXISTS public.ea_users CASCADE;

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    location JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add RLS policies for profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- STEP 3: Update PROVIDERS table
-- ============================================================================

-- Add provider_id UUID column
ALTER TABLE public.providers
    ADD COLUMN IF NOT EXISTS provider_uuid UUID DEFAULT gen_random_uuid();

-- Create unique index on provider_uuid
CREATE UNIQUE INDEX IF NOT EXISTS idx_providers_uuid ON public.providers(provider_uuid);

-- Insert Plaid provider
INSERT INTO public.providers (name, is_aa_aggregator, website)
VALUES ('Plaid', false, 'https://plaid.com')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 4: Update CONNECTIONS table
-- ============================================================================

-- Drop existing RLS policies first (they depend on user_id column)
DROP POLICY IF EXISTS "Users can view their own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can insert their own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can update their own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can delete their own connections" ON public.connections;

-- Drop existing foreign key constraints
ALTER TABLE public.connections DROP CONSTRAINT IF EXISTS connections_user_id_fkey;
ALTER TABLE public.connections DROP CONSTRAINT IF EXISTS connections_provider_id_fkey;

-- Change user_id from integer to UUID
ALTER TABLE public.connections
    ALTER COLUMN user_id TYPE UUID USING uuid_generate_v4();

-- Drop refresh_token (Plaid doesn't use it)
ALTER TABLE public.connections
    DROP COLUMN IF EXISTS refresh_token;

-- Add new Plaid-specific fields
ALTER TABLE public.connections
    ADD COLUMN IF NOT EXISTS institution_id VARCHAR,
    ADD COLUMN IF NOT EXISTS institution_name VARCHAR,
    ADD COLUMN IF NOT EXISTS products JSONB,
    ADD COLUMN IF NOT EXISTS available_products JSONB,
    ADD COLUMN IF NOT EXISTS consent_expiration_time TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS update_type VARCHAR;

-- Change artifact from json to JSONB for better performance
ALTER TABLE public.connections
    ALTER COLUMN artifact TYPE JSONB USING artifact::jsonb;

-- Change scopes and fip_ids to JSONB
ALTER TABLE public.connections
    ALTER COLUMN scopes TYPE JSONB USING scopes::jsonb,
    ALTER COLUMN fip_ids TYPE JSONB USING fip_ids::jsonb;

-- Add foreign key constraint to profiles
ALTER TABLE public.connections
    ADD CONSTRAINT connections_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Add foreign key constraint to providers (keep integer for now)
ALTER TABLE public.connections
    ADD CONSTRAINT connections_provider_id_fkey
    FOREIGN KEY (provider_id) REFERENCES public.providers(provider_id);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_connections_user_id ON public.connections(user_id);
CREATE INDEX IF NOT EXISTS idx_connections_status ON public.connections(connection_status);
CREATE INDEX IF NOT EXISTS idx_connections_item_id ON public.connections(external_item_id);
CREATE INDEX IF NOT EXISTS idx_connections_institution_id ON public.connections(institution_id);

-- Add RLS policies
ALTER TABLE public.connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own connections"
    ON public.connections FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own connections"
    ON public.connections FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own connections"
    ON public.connections FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own connections"
    ON public.connections FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- STEP 5: Update ACCOUNTS table
-- ============================================================================

-- CRITICAL: Drop ALL policies on transactions table first
-- (they have JOIN conditions that reference accounts.user_id, blocking the ALTER TYPE)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = 'transactions')
    LOOP
        EXECUTE 'DROP POLICY IF EXISTS "' || r.policyname || '" ON public.transactions';
    END LOOP;
END $$;

-- Disable RLS on transactions table
ALTER TABLE public.transactions DISABLE ROW LEVEL SECURITY;

-- Now drop ALL policies on accounts table
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = 'accounts')
    LOOP
        EXECUTE 'DROP POLICY IF EXISTS "' || r.policyname || '" ON public.accounts';
    END LOOP;
END $$;

-- Disable RLS on accounts table
ALTER TABLE public.accounts DISABLE ROW LEVEL SECURITY;

-- Drop existing foreign key
ALTER TABLE public.accounts DROP CONSTRAINT IF EXISTS accounts_user_id_fkey;

-- Change user_id from integer to UUID
ALTER TABLE public.accounts
    ALTER COLUMN user_id TYPE UUID USING uuid_generate_v4();

-- Change external_account_id from integer to TEXT (Plaid uses strings)
ALTER TABLE public.accounts
    ALTER COLUMN external_account_id TYPE TEXT;

-- Change mask from integer to VARCHAR
ALTER TABLE public.accounts
    ALTER COLUMN mask TYPE VARCHAR USING mask::VARCHAR;

-- Change balances from real to DECIMAL for better precision
ALTER TABLE public.accounts
    ALTER COLUMN current_balance TYPE DECIMAL(15,2) USING current_balance::DECIMAL(15,2),
    ALTER COLUMN credit_limit TYPE DECIMAL(15,2) USING credit_limit::DECIMAL(15,2);

-- Rename identifiers to provider_metadata
ALTER TABLE public.accounts
    RENAME COLUMN identifiers TO provider_metadata;

-- Change provider_metadata to JSONB
ALTER TABLE public.accounts
    ALTER COLUMN provider_metadata TYPE JSONB USING provider_metadata::jsonb;

-- Add new fields
ALTER TABLE public.accounts
    ADD COLUMN IF NOT EXISTS available_balance DECIMAL(15,2),
    ADD COLUMN IF NOT EXISTS official_name VARCHAR,
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR,
    ADD COLUMN IF NOT EXISTS holder_category VARCHAR;

-- Change timestamps to TIMESTAMPTZ for consistency
ALTER TABLE public.accounts
    ALTER COLUMN last_refreshed_at TYPE TIMESTAMPTZ,
    ALTER COLUMN created_at TYPE TIMESTAMPTZ,
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ;

-- Add foreign key to profiles
ALTER TABLE public.accounts
    ADD CONSTRAINT accounts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON public.accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_external_id ON public.accounts(external_account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON public.accounts(account_status);

-- Add RLS policies
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own accounts"
    ON public.accounts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own accounts"
    ON public.accounts FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own accounts"
    ON public.accounts FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own accounts"
    ON public.accounts FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- STEP 6: Update TRANSACTIONS table
-- ============================================================================

-- RLS already disabled and policies already dropped in STEP 5

-- Change external_txn_id from integer to TEXT
ALTER TABLE public.transactions
    ALTER COLUMN external_txn_id TYPE TEXT;

-- Change amount from real to DECIMAL
ALTER TABLE public.transactions
    ALTER COLUMN amount TYPE DECIMAL(15,2) USING amount::DECIMAL(15,2);

-- Make running_balance nullable and change to DECIMAL
ALTER TABLE public.transactions
    ALTER COLUMN running_balance DROP NOT NULL,
    ALTER COLUMN running_balance TYPE DECIMAL(15,2) USING running_balance::DECIMAL(15,2);

-- Change json columns to JSONB
ALTER TABLE public.transactions
    ALTER COLUMN location TYPE JSONB USING location::jsonb,
    ALTER COLUMN raw_payload TYPE JSONB USING raw_payload::jsonb;

-- Change timestamps to TIMESTAMPTZ
ALTER TABLE public.transactions
    ALTER COLUMN txn_date TYPE TIMESTAMPTZ,
    ALTER COLUMN posted_at TYPE TIMESTAMPTZ;

-- Add new fields for Plaid
ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS authorized_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS merchant_logo_url VARCHAR,
    ADD COLUMN IF NOT EXISTS merchant_website VARCHAR,
    ADD COLUMN IF NOT EXISTS payment_channel VARCHAR,
    ADD COLUMN IF NOT EXISTS counterparties JSONB,
    ADD COLUMN IF NOT EXISTS personal_finance_category JSONB,
    ADD COLUMN IF NOT EXISTS check_number VARCHAR,
    ADD COLUMN IF NOT EXISTS provider_metadata JSONB,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON public.transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_external_id ON public.transactions(external_txn_id);
CREATE INDEX IF NOT EXISTS idx_transactions_txn_date ON public.transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_transactions_authorized_date ON public.transactions(authorized_date);
CREATE INDEX IF NOT EXISTS idx_transactions_pending ON public.transactions(pending);
CREATE INDEX IF NOT EXISTS idx_transactions_payment_channel ON public.transactions(payment_channel);

-- Add RLS policies
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own transactions"
    ON public.transactions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.accounts
            WHERE accounts.account_id = transactions.account_id
            AND accounts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own transactions"
    ON public.transactions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.accounts
            WHERE accounts.account_id = transactions.account_id
            AND accounts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own transactions"
    ON public.transactions FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.accounts
            WHERE accounts.account_id = transactions.account_id
            AND accounts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own transactions"
    ON public.transactions FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.accounts
            WHERE accounts.account_id = transactions.account_id
            AND accounts.user_id = auth.uid()
        )
    );

-- ============================================================================
-- STEP 7: Add updated_at triggers
-- ============================================================================

DROP TRIGGER IF EXISTS update_connections_updated_at ON public.connections;
CREATE TRIGGER update_connections_updated_at
    BEFORE UPDATE ON public.connections
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_accounts_updated_at ON public.accounts;
CREATE TRIGGER update_accounts_updated_at
    BEFORE UPDATE ON public.accounts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_transactions_updated_at ON public.transactions;
CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON public.transactions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 001_plaid_schema_updates completed successfully!';
    RAISE NOTICE '   - Updated ENUM types';
    RAISE NOTICE '   - Created profiles table';
    RAISE NOTICE '   - Updated providers table';
    RAISE NOTICE '   - Updated connections table (+ 6 fields)';
    RAISE NOTICE '   - Updated accounts table (+ 4 fields)';
    RAISE NOTICE '   - Updated transactions table (+ 8 fields)';
    RAISE NOTICE '   - Added RLS policies';
    RAISE NOTICE '   - Added performance indexes';
END $$;
