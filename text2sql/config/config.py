"""
Configuration settings for text2sql with Supabase
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Text2SQLConfig:
    """Configuration for Text2SQL system"""

    # Supabase Database Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")

    # Parse Supabase URL to get database connection details
    # Supabase PostgreSQL format: postgresql://[user]:[password]@[host]:[port]/[database]
    # We'll use the Supabase URL to extract connection details

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
    OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

    # Cache Configuration
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

    @classmethod
    def get_supabase_db_config(cls):
        """Extract PostgreSQL connection details from Supabase"""
        # Supabase Pooler connection
        # URL format: https://<project-ref>.supabase.co
        # PostgreSQL pooler: aws-1-us-east-1.pooler.supabase.com:5432

        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL not set in environment")

        if not cls.SUPABASE_DB_PASSWORD:
            raise ValueError("SUPABASE_DB_PASSWORD not set in environment. Get this from Supabase Dashboard → Settings → Database → Connection String")

        # Extract project ref from URL
        project_ref = cls.SUPABASE_URL.replace("https://", "").split(".")[0]

        return {
            "host": "aws-1-us-east-1.pooler.supabase.com",
            "port": 5432,
            "database": "postgres",
            "user": f"postgres.{project_ref}",
            "password": cls.SUPABASE_DB_PASSWORD,
        }


def get_schema_info() -> str:
    """
    Get database schema information for our Nidhi-Fi fake data
    This is used as context for SQL generation
    """
    return """
Database Schema for Nidhi-Fi Financial Data:
==========================================

Table: accounts
---------------
- account_id (uuid, primary key)
- user_id (uuid, foreign key to profiles.id, NOT NULL) ← CRITICAL: Always filter by this
- external_account_id (text, NOT NULL)
- name (varchar, NOT NULL) - Account display name
- account_type (text, NOT NULL) - 'depository' or 'credit'
- account_subtype (text) - 'checking', 'savings', 'credit_card', etc.
- currency (varchar(3), NOT NULL) - 'USD' or 'INR'
- mask (varchar) - Last 4 digits of account number
- current_balance (numeric(15,2), NOT NULL)
- available_balance (numeric(15,2))
- credit_limit (numeric(15,2)) - For credit cards
- institution_name (varchar) - Bank name (e.g., 'Chase', 'ICICI Bank')
- institution_country (varchar(2)) - 'US' or 'IN'
- account_status (enum) - 'Active' or 'Inactive'
- created_at (timestamp with time zone)
- last_refreshed_at (timestamp with time zone)

IMPORTANT NOTE ON ACCOUNTS:
- Users select specific accounts during onboarding from a list of available accounts
- Only selected accounts have transactions
- When user asks for "my accounts", return ONLY accounts that have transactions
- Non-selected accounts exist in the database but have 0 transactions

Table: transactions
-------------------
- transaction_id (uuid, primary key)
- account_id (uuid, foreign key to accounts.account_id, NOT NULL)
- external_txn_id (text, NOT NULL)
- txn_date (timestamp with time zone, NOT NULL) - Transaction date
- posted_at (timestamp with time zone, NOT NULL) - When transaction posted
- authorized_date (timestamp with time zone) - Authorization date
- amount (numeric(15,2), NOT NULL) - Transaction amount
- currency (varchar(3), NOT NULL) - 'USD' or 'INR'
- txn_direction (enum, NOT NULL) - 'Credit' or 'Debit'
- description_raw (text) - Original transaction description
- merchant_name_raw (varchar) - Merchant name
- merchant_logo_url (varchar)
- merchant_website (varchar)
- pending (boolean, NOT NULL) - If transaction is pending
- running_balance (numeric(15,2)) - Balance after transaction
- category (text) - Transaction category (e.g., 'Food and Drink', 'Shopping')
- personal_finance_category (jsonb) - Detailed category info
- location (jsonb) - Transaction location details
- payment_channel (varchar) - 'online', 'in store', 'other'
- counterparties (jsonb) - Transaction counterparties
- check_number (varchar)
- provider_metadata (jsonb) - Additional metadata
- raw_payload (jsonb, NOT NULL) - Full transaction data
- created_at (timestamp with time zone)

Table: connections
------------------
- connection_id (uuid, primary key)
- provider_id (integer, foreign key to providers.provider_id)
- user_id (uuid, foreign key to profiles.id, NOT NULL)
- access_token (varchar)
- external_item_id (varchar) - External connection identifier
- connection_status (enum) - 'Active', 'Inactive', etc.
- institution_id (varchar) - Institution identifier
- institution_name (varchar) - Bank/institution name
- products (jsonb) - Available products
- linked_at (timestamp with time zone)
- last_synced_at (timestamp with time zone)
- created_at (timestamp with time zone)

Table: providers
----------------
- provider_id (uuid, primary key)
- name (varchar, NOT NULL) - Provider name
- is_aa_aggregator (boolean)
- website (varchar)
- created_at (timestamp with time zone)

CRITICAL RULES FOR SQL GENERATION:
===================================

1. USER DATA ISOLATION (MOST IMPORTANT):
   - ALWAYS filter by user_id in the WHERE clause
   - For accounts: WHERE accounts.user_id = %s
   - For transactions: JOIN with accounts and filter accounts.user_id = %s
   - For connections: WHERE connections.user_id = %s

2. JOIN PATTERNS:
   - Transactions to accounts: transactions.account_id = accounts.account_id
   - Accounts to connections: accounts.institution_name = connections.institution_name

3. COLUMN NAMES (Use exact names):
   - Transaction ID: 'transaction_id' (NOT 'id' or 'txn_id')
   - Merchant: 'merchant_name_raw' (NOT 'merchant')
   - Date: 'txn_date' (NOT 'transaction_date' or 'date')

4. PARAMETERIZED QUERIES:
   - Always use %s placeholders for user_id
   - Return SQL with placeholders, not hardcoded values

5. HELPFUL ALIASES:
   - Use meaningful column aliases for better readability
   - Format currency amounts appropriately

6. COMMON QUERY PATTERNS:
   - "my accounts" → SELECT DISTINCT accounts WHERE user has transactions (JOIN with transactions)
   - "transactions" → JOIN transactions with accounts, filter by user_id
   - "spending" → SUM(amount) WHERE txn_direction = 'Debit'
   - "income" → SUM(amount) WHERE txn_direction = 'Credit'
   - "balance" → SELECT current_balance from accounts (only selected accounts)

7. DATE FILTERING:
   - Use txn_date for transaction date queries
   - Support ranges: "last month", "this year", "last 30 days"
   - Use timestamp with time zone operations

Example Queries:
----------------
User: "Show me my accounts"
SQL: SELECT DISTINCT a.account_id, a.name, a.account_type, a.current_balance, a.currency, a.institution_name
     FROM accounts a
     INNER JOIN transactions t ON a.account_id = t.account_id
     WHERE a.user_id = %s
     ORDER BY a.current_balance DESC;

User: "What's my total spending this month?"
SQL: SELECT SUM(amount) as total_spending
     FROM transactions t
     JOIN accounts a ON t.account_id = a.account_id
     WHERE a.user_id = %s
     AND t.txn_direction = 'Debit'
     AND t.txn_date >= date_trunc('month', CURRENT_DATE);

User: "Show my recent transactions"
SQL: SELECT t.txn_date, t.merchant_name_raw, t.amount, t.category, a.name as account_name
     FROM transactions t
     JOIN accounts a ON t.account_id = a.account_id
     WHERE a.user_id = %s
     ORDER BY t.txn_date DESC
     LIMIT 20;
"""


config = Text2SQLConfig()
