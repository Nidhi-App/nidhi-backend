/*
Fix RLS policies for development - Phase 4

Issue: Row Level Security (RLS) is blocking inserts to connections table.

Solution: Add proper RLS policies that allow:
1. Service role (backend) to do everything
2. Users to manage their own connections

Run this in Supabase SQL Editor or via migration tool.
*/

-- ============================================================
-- OPTION 1: Disable RLS for development (TEMPORARY)
-- ============================================================
-- Uncomment this if you want to temporarily disable RLS for testing
-- WARNING: Only use in development!

-- ALTER TABLE public.connections DISABLE ROW LEVEL SECURITY;


-- ============================================================
-- OPTION 2: Add proper RLS policies (RECOMMENDED)
-- ============================================================

-- Drop existing policies if any
DROP POLICY IF EXISTS "connections_select_own" ON public.connections;
DROP POLICY IF EXISTS "connections_insert_own" ON public.connections;
DROP POLICY IF EXISTS "connections_update_own" ON public.connections;
DROP POLICY IF EXISTS "connections_delete_own" ON public.connections;
DROP POLICY IF EXISTS "connections_service_all" ON public.connections;

-- Policy 1: Allow service role (backend) to do everything
-- This allows your backend API key to perform all operations
CREATE POLICY "connections_service_all"
ON public.connections
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy 2: Allow authenticated users to SELECT their own connections
CREATE POLICY "connections_select_own"
ON public.connections
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 3: Allow authenticated users to INSERT their own connections
CREATE POLICY "connections_insert_own"
ON public.connections
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy 4: Allow authenticated users to UPDATE their own connections
CREATE POLICY "connections_update_own"
ON public.connections
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy 5: Allow authenticated users to DELETE their own connections
CREATE POLICY "connections_delete_own"
ON public.connections
FOR DELETE
TO authenticated
USING (auth.uid() = user_id);


-- ============================================================
-- Apply same policies to accounts and transactions tables
-- ============================================================

-- ACCOUNTS TABLE
DROP POLICY IF EXISTS "accounts_select_own" ON public.accounts;
DROP POLICY IF EXISTS "accounts_insert_own" ON public.accounts;
DROP POLICY IF EXISTS "accounts_update_own" ON public.accounts;
DROP POLICY IF EXISTS "accounts_delete_own" ON public.accounts;
DROP POLICY IF EXISTS "accounts_service_all" ON public.accounts;

CREATE POLICY "accounts_service_all"
ON public.accounts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "accounts_select_own"
ON public.accounts
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "accounts_insert_own"
ON public.accounts
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "accounts_update_own"
ON public.accounts
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "accounts_delete_own"
ON public.accounts
FOR DELETE
TO authenticated
USING (auth.uid() = user_id);


-- TRANSACTIONS TABLE
DROP POLICY IF EXISTS "transactions_select_own" ON public.transactions;
DROP POLICY IF EXISTS "transactions_insert_own" ON public.transactions;
DROP POLICY IF EXISTS "transactions_update_own" ON public.transactions;
DROP POLICY IF EXISTS "transactions_delete_own" ON public.transactions;
DROP POLICY IF EXISTS "transactions_service_all" ON public.transactions;

CREATE POLICY "transactions_service_all"
ON public.transactions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "transactions_select_own"
ON public.transactions
FOR SELECT
TO authenticated
USING (
    auth.uid() IN (
        SELECT user_id FROM public.accounts WHERE account_id = transactions.account_id
    )
);

CREATE POLICY "transactions_insert_own"
ON public.transactions
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() IN (
        SELECT user_id FROM public.accounts WHERE account_id = transactions.account_id
    )
);

CREATE POLICY "transactions_update_own"
ON public.transactions
FOR UPDATE
TO authenticated
USING (
    auth.uid() IN (
        SELECT user_id FROM public.accounts WHERE account_id = transactions.account_id
    )
)
WITH CHECK (
    auth.uid() IN (
        SELECT user_id FROM public.accounts WHERE account_id = transactions.account_id
    )
);

CREATE POLICY "transactions_delete_own"
ON public.transactions
FOR DELETE
TO authenticated
USING (
    auth.uid() IN (
        SELECT user_id FROM public.accounts WHERE account_id = transactions.account_id
    )
);


-- ============================================================
-- Verify policies are created
-- ============================================================
SELECT
    schemaname,
    tablename,
    policyname,
    cmd,
    roles
FROM pg_policies
WHERE tablename IN ('connections', 'accounts', 'transactions')
ORDER BY tablename, policyname;
