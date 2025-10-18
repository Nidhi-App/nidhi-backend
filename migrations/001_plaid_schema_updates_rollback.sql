-- ============================================================================
-- Rollback Migration: 001_plaid_schema_updates_rollback.sql
-- Description: Rollback Plaid schema changes
-- Author: Development Team
-- Date: 2025-01-17
-- WARNING: This will revert all changes made in 001_plaid_schema_updates.sql
-- ============================================================================

-- NOTE: ENUM values cannot be removed in PostgreSQL
-- You would need to recreate the entire ENUM type to remove values
-- For safety, we'll leave the new ENUM values in place

-- ============================================================================
-- STEP 1: Drop RLS policies
-- ============================================================================

-- Drop connections policies
DROP POLICY IF EXISTS "Users can view own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can insert own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can update own connections" ON public.connections;
DROP POLICY IF EXISTS "Users can delete own connections" ON public.connections;

-- Drop accounts policies
DROP POLICY IF EXISTS "Users can view own accounts" ON public.accounts;
DROP POLICY IF EXISTS "Users can insert own accounts" ON public.accounts;
DROP POLICY IF EXISTS "Users can update own accounts" ON public.accounts;
DROP POLICY IF EXISTS "Users can delete own accounts" ON public.accounts;

-- Drop transactions policies
DROP POLICY IF EXISTS "Users can view own transactions" ON public.transactions;
DROP POLICY IF EXISTS "Users can insert own transactions" ON public.transactions;
DROP POLICY IF EXISTS "Users can update own transactions" ON public.transactions;
DROP POLICY IF EXISTS "Users can delete own transactions" ON public.transactions;

-- Drop profiles policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;

-- ============================================================================
-- STEP 2: Drop triggers
-- ============================================================================

DROP TRIGGER IF EXISTS update_connections_updated_at ON public.connections;
DROP TRIGGER IF EXISTS update_accounts_updated_at ON public.accounts;
DROP TRIGGER IF EXISTS update_transactions_updated_at ON public.transactions;
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;

-- ============================================================================
-- STEP 3: Drop indexes
-- ============================================================================

-- Connections indexes
DROP INDEX IF EXISTS idx_connections_user_id;
DROP INDEX IF EXISTS idx_connections_status;
DROP INDEX IF EXISTS idx_connections_item_id;
DROP INDEX IF EXISTS idx_connections_institution_id;

-- Accounts indexes
DROP INDEX IF EXISTS idx_accounts_user_id;
DROP INDEX IF EXISTS idx_accounts_external_id;
DROP INDEX IF EXISTS idx_accounts_status;

-- Transactions indexes
DROP INDEX IF EXISTS idx_transactions_account_id;
DROP INDEX IF EXISTS idx_transactions_external_id;
DROP INDEX IF EXISTS idx_transactions_txn_date;
DROP INDEX IF EXISTS idx_transactions_authorized_date;
DROP INDEX IF EXISTS idx_transactions_pending;
DROP INDEX IF EXISTS idx_transactions_payment_channel;

-- Providers indexes
DROP INDEX IF EXISTS idx_providers_uuid;

-- ============================================================================
-- STEP 4: Revert TRANSACTIONS table
-- ============================================================================

-- Remove new columns
ALTER TABLE public.transactions
    DROP COLUMN IF EXISTS authorized_date,
    DROP COLUMN IF EXISTS merchant_logo_url,
    DROP COLUMN IF EXISTS merchant_website,
    DROP COLUMN IF EXISTS payment_channel,
    DROP COLUMN IF EXISTS counterparties,
    DROP COLUMN IF EXISTS personal_finance_category,
    DROP COLUMN IF EXISTS check_number,
    DROP COLUMN IF EXISTS provider_metadata,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

-- Revert data types (WARNING: May cause data loss)
ALTER TABLE public.transactions
    ALTER COLUMN external_txn_id TYPE INTEGER USING external_txn_id::INTEGER,
    ALTER COLUMN amount TYPE REAL USING amount::REAL,
    ALTER COLUMN running_balance TYPE REAL USING COALESCE(running_balance::REAL, 0),
    ALTER COLUMN running_balance SET NOT NULL,
    ALTER COLUMN location TYPE JSON USING location::JSON,
    ALTER COLUMN raw_payload TYPE JSON USING raw_payload::JSON,
    ALTER COLUMN txn_date TYPE TIMESTAMP WITHOUT TIME ZONE,
    ALTER COLUMN posted_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- ============================================================================
-- STEP 5: Revert ACCOUNTS table
-- ============================================================================

-- Remove new columns
ALTER TABLE public.accounts
    DROP COLUMN IF EXISTS available_balance,
    DROP COLUMN IF EXISTS official_name,
    DROP COLUMN IF EXISTS verification_status,
    DROP COLUMN IF EXISTS holder_category;

-- Revert column rename
ALTER TABLE public.accounts
    RENAME COLUMN provider_metadata TO identifiers;

-- Revert data types (WARNING: May cause data loss)
ALTER TABLE public.accounts
    ALTER COLUMN user_id TYPE INTEGER USING hashtext(user_id::TEXT),
    ALTER COLUMN external_account_id TYPE INTEGER USING external_account_id::INTEGER,
    ALTER COLUMN mask TYPE INTEGER USING COALESCE(mask::INTEGER, 0),
    ALTER COLUMN current_balance TYPE REAL USING current_balance::REAL,
    ALTER COLUMN credit_limit TYPE REAL USING credit_limit::REAL,
    ALTER COLUMN identifiers TYPE JSON USING identifiers::JSON,
    ALTER COLUMN last_refreshed_at TYPE TIMESTAMP WITHOUT TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- ============================================================================
-- STEP 6: Revert CONNECTIONS table
-- ============================================================================

-- Remove new columns
ALTER TABLE public.connections
    DROP COLUMN IF EXISTS institution_id,
    DROP COLUMN IF EXISTS institution_name,
    DROP COLUMN IF EXISTS products,
    DROP COLUMN IF EXISTS available_products,
    DROP COLUMN IF EXISTS consent_expiration_time,
    DROP COLUMN IF EXISTS update_type;

-- Add back refresh_token
ALTER TABLE public.connections
    ADD COLUMN IF NOT EXISTS refresh_token VARCHAR;

-- Revert data types
ALTER TABLE public.connections
    ALTER COLUMN user_id TYPE INTEGER USING hashtext(user_id::TEXT),
    ALTER COLUMN artifact TYPE JSON USING artifact::JSON,
    ALTER COLUMN scopes TYPE JSON USING scopes::JSON,
    ALTER COLUMN fip_ids TYPE JSON USING fip_ids::JSON;

-- ============================================================================
-- STEP 7: Recreate ea_users table
-- ============================================================================

-- Drop profiles table
DROP TABLE IF EXISTS public.profiles CASCADE;

-- Recreate ea_users
CREATE SEQUENCE IF NOT EXISTS public.ea_users_user_id_seq
    AS INTEGER
    START WITH 1
    INCREMENT BY 1;

CREATE TABLE public.ea_users (
    user_id INTEGER NOT NULL DEFAULT nextval('ea_users_user_id_seq'),
    first_name VARCHAR NOT NULL,
    last_name VARCHAR,
    email VARCHAR,
    location JSON,
    CONSTRAINT ea_users_pkey PRIMARY KEY (user_id)
);

ALTER SEQUENCE public.ea_users_user_id_seq OWNED BY public.ea_users.user_id;

-- ============================================================================
-- STEP 8: Revert PROVIDERS table
-- ============================================================================

-- Remove provider_uuid column
ALTER TABLE public.providers
    DROP COLUMN IF EXISTS provider_uuid;

-- Remove Plaid provider (optional - comment out if you want to keep it)
-- DELETE FROM public.providers WHERE name = 'Plaid';

-- ============================================================================
-- STEP 9: Re-add foreign key constraints
-- ============================================================================

-- Add foreign keys back to ea_users
ALTER TABLE public.connections
    DROP CONSTRAINT IF EXISTS connections_user_id_fkey,
    ADD CONSTRAINT connections_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.ea_users(user_id);

ALTER TABLE public.accounts
    DROP CONSTRAINT IF EXISTS accounts_user_id_fkey,
    ADD CONSTRAINT accounts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.ea_users(user_id);

-- ============================================================================
-- STEP 10: Drop helper function
-- ============================================================================

DROP FUNCTION IF EXISTS public.update_updated_at_column() CASCADE;

-- ============================================================================
-- Rollback Complete
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '⚠️  Rollback 001_plaid_schema_updates completed!';
    RAISE NOTICE '   WARNING: Some data may have been lost during type conversions';
    RAISE NOTICE '   - Reverted to ea_users table';
    RAISE NOTICE '   - Removed Plaid-specific fields';
    RAISE NOTICE '   - Reverted data types';
    RAISE NOTICE '   - Removed RLS policies';
    RAISE NOTICE '   - Removed indexes';
END $$;
