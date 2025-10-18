# Database Migrations

This folder contains SQL migration scripts for the Nidhi Backend database schema.

## Migrations

### 001_plaid_schema_updates.sql
**Status**: Ready to apply
**Description**: Updates schema for Plaid integration
**Date**: 2025-01-17

**Changes**:
- Replace `ea_users` with `profiles` table (Supabase Auth compatible)
- Update `connections` table: user_id → UUID, +6 Plaid fields
- Update `accounts` table: Fix data types, +4 new fields
- Update `transactions` table: Fix data types, +8 Plaid fields
- Add RLS (Row Level Security) policies
- Add performance indexes
- Add updated_at triggers

**Rollback**: `001_plaid_schema_updates_rollback.sql`

---

## How to Apply Migrations

### Option 1: Via Supabase Dashboard (Recommended)
1. Go to https://supabase.com/dashboard
2. Select your project
3. Navigate to **SQL Editor**
4. Copy the contents of `001_plaid_schema_updates.sql`
5. Paste and click **Run**

### Option 2: Via psql command line
```bash
psql postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres \
  -f migrations/001_plaid_schema_updates.sql
```

### Option 3: Via Supabase CLI
```bash
supabase db push
```

---

## How to Rollback

**⚠️ WARNING**: Rollback may cause data loss due to type conversions.

```bash
psql postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres \
  -f migrations/001_plaid_schema_updates_rollback.sql
```

---

## Verification

After applying the migration, verify:

1. **Check tables exist**:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('profiles', 'connections', 'accounts', 'transactions', 'providers');
   ```

2. **Check new columns in connections**:
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'connections'
   AND column_name IN ('institution_id', 'institution_name', 'products');
   ```

3. **Check RLS is enabled**:
   ```sql
   SELECT tablename, rowsecurity
   FROM pg_tables
   WHERE schemaname = 'public';
   ```

4. **Check Plaid provider exists**:
   ```sql
   SELECT * FROM providers WHERE name = 'Plaid';
   ```

---

## Migration History

| Version | Date | Description | Status |
|---------|------|-------------|--------|
| 001 | 2025-01-17 | Plaid schema updates | ✅ Ready |

---

## Notes

- Always backup your database before running migrations
- Test migrations in a development environment first
- ENUM values cannot be removed in PostgreSQL (rollback limitation)
- UUID conversions in rollback use hashtext() - data will not match original integers
