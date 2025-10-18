# Plaid Integration Development Plan

## Project Overview

**Goal**: Build a FastAPI backend that integrates with Plaid to fetch and normalize financial data (accounts & transactions) into Supabase PostgreSQL.

**Tech Stack**: FastAPI + Plaid SDK + Pydantic + Supabase + APScheduler

**Team**: 2 developers (Data Engineer + AI Engineer)

**Timeline**: 6-8 weeks

---

## Development Phases

---

## Phase 0: Setup & Prerequisites (Week 1, Days 1-2)

### Goals
- Set up development environment
- Configure Plaid sandbox account
- Set up project structure

### Tasks

#### 0.1 Plaid Account Setup
- [ ] Sign up for Plaid account at https://dashboard.plaid.com/signup
- [ ] Get Plaid credentials (sandbox environment):
  - `PLAID_CLIENT_ID`
  - `PLAID_SECRET`
  - `PLAID_ENV=sandbox`
- [ ] Review Plaid Quickstart: https://plaid.com/docs/quickstart/
- [ ] Test Plaid API using Postman/curl

#### 0.2 Project Scaffolding
- [ ] Initialize Python project with Poetry
  ```bash
  cd nidhi-backend
  poetry init
  poetry add fastapi uvicorn[standard] plaid-python supabase pydantic pydantic-settings python-jose[cryptography] python-multipart apscheduler httpx loguru sentry-sdk
  poetry add --group dev pytest pytest-asyncio black ruff mypy
  ```

- [ ] Create project structure:
  ```
  nidhi-backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── api/
  │   │   ├── __init__.py
  │   │   └── v1/
  │   │       ├── __init__.py
  │   │       ├── auth.py
  │   │       ├── connections.py
  │   │       ├── accounts.py
  │   │       ├── transactions.py
  │   │       └── webhooks.py
  │   ├── core/
  │   │   ├── __init__.py
  │   │   ├── database.py
  │   │   ├── security.py
  │   │   └── scheduler.py
  │   ├── providers/
  │   │   ├── __init__.py
  │   │   ├── plaid/
  │   │   │   ├── __init__.py
  │   │   │   ├── client.py
  │   │   │   ├── models.py
  │   │   │   ├── normalizer.py
  │   │   │   └── webhooks.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   ├── account.py
  │   │   ├── transaction.py
  │   │   ├── connection.py
  │   │   └── enums.py
  │   ├── services/
  │   │   ├── __init__.py
  │   │   ├── account_service.py
  │   │   ├── transaction_service.py
  │   │   ├── connection_service.py
  │   │   └── sync_service.py
  │   ├── schemas/
  │   │   ├── __init__.py
  │   │   ├── account.py
  │   │   ├── transaction.py
  │   │   └── connection.py
  │   └── utils/
  │       ├── __init__.py
  │       └── logger.py
  ├── tests/
  ├── .env.example
  ├── .gitignore
  ├── pyproject.toml
  └── README.md
  ```

#### 0.3 Environment Configuration
- [ ] Create `.env` file with all required variables
- [ ] Set up Pydantic BaseSettings for config management
- [ ] Configure logging with Loguru

**Deliverables:**
- ✅ Working FastAPI app (Hello World)
- ✅ Plaid sandbox credentials configured
- ✅ Project structure scaffolded

---

## Phase 1: Supabase Schema Updates (Week 1, Days 3-5)

### Goals
- Update existing schema to support Plaid integration
- Fix data types (UUID, TEXT)
- Add missing fields for accounts and transactions
- Create migration scripts

### Tasks

#### 1.1 Schema Analysis
- [ ] Review current schema in `xpenseapp_db/docker/init-custom-tables.sql`
- [ ] Document current vs required fields (reference: plaid-integration-flow-detailed.md)
- [ ] Identify breaking changes vs additive changes

#### 1.2 Schema Changes - Connections Table
**Required Changes:**
```sql
-- Add Plaid-specific fields
ALTER TABLE public.connections
    ADD COLUMN IF NOT EXISTS institution_id VARCHAR,
    ADD COLUMN IF NOT EXISTS institution_name VARCHAR,
    ADD COLUMN IF NOT EXISTS products JSONB,
    ADD COLUMN IF NOT EXISTS available_products JSONB,
    ADD COLUMN IF NOT EXISTS consent_expiration_time TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS update_type VARCHAR;

-- Update existing columns to use UUID
ALTER TABLE public.connections
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid;

-- Add missing enums to connection_status
ALTER TYPE public.connection_status ADD VALUE IF NOT EXISTS 'Initializing';
ALTER TYPE public.connection_status ADD VALUE IF NOT EXISTS 'Pending';

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_connections_user_id ON public.connections(user_id);
CREATE INDEX IF NOT EXISTS idx_connections_access_token ON public.connections(access_token);
CREATE INDEX IF NOT EXISTS idx_connections_item_id ON public.connections(external_item_id);
CREATE INDEX IF NOT EXISTS idx_connections_institution_id ON public.connections(institution_id);
CREATE INDEX IF NOT EXISTS idx_connections_status ON public.connections(connection_status);
```

#### 1.3 Schema Changes - Accounts Table
**Required Changes:**
```sql
-- Fix data types
ALTER TABLE public.accounts
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ALTER COLUMN external_account_id TYPE TEXT,
    ALTER COLUMN mask TYPE VARCHAR;

-- Add missing fields
ALTER TABLE public.accounts
    ADD COLUMN IF NOT EXISTS official_name VARCHAR,
    ADD COLUMN IF NOT EXISTS available_balance DECIMAL(15,2),
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR,
    ADD COLUMN IF NOT EXISTS holder_category VARCHAR,
    ADD COLUMN IF NOT EXISTS provider_metadata JSONB;

-- Update identifiers column name for clarity
ALTER TABLE public.accounts
    RENAME COLUMN identifiers TO provider_metadata;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON public.accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_external_id ON public.accounts(external_account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON public.accounts(account_status);
```

#### 1.4 Schema Changes - Transactions Table
**Required Changes:**
```sql
-- Fix data types
ALTER TABLE public.transactions
    ALTER COLUMN external_txn_id TYPE TEXT;

-- Add missing fields
ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS authorized_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS merchant_logo_url VARCHAR,
    ADD COLUMN IF NOT EXISTS merchant_website VARCHAR,
    ADD COLUMN IF NOT EXISTS payment_channel VARCHAR,
    ADD COLUMN IF NOT EXISTS counterparties JSONB,
    ADD COLUMN IF NOT EXISTS personal_finance_category JSONB,
    ADD COLUMN IF NOT EXISTS check_number VARCHAR,
    ADD COLUMN IF NOT EXISTS provider_metadata JSONB;

-- Make running_balance nullable (not always available)
ALTER TABLE public.transactions
    ALTER COLUMN running_balance DROP NOT NULL;

-- Update raw_payload column to use JSONB
ALTER TABLE public.transactions
    ALTER COLUMN raw_payload TYPE JSONB USING raw_payload::jsonb;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON public.transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_external_id ON public.transactions(external_txn_id);
CREATE INDEX IF NOT EXISTS idx_transactions_txn_date ON public.transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_transactions_authorized_date ON public.transactions(authorized_date);
CREATE INDEX IF NOT EXISTS idx_transactions_payment_channel ON public.transactions(payment_channel);
CREATE INDEX IF NOT EXISTS idx_transactions_pending ON public.transactions(pending);
```

#### 1.5 Add Plaid Provider
```sql
-- Insert Plaid as provider
INSERT INTO public.providers (name, is_aa_aggregator, website)
VALUES ('Plaid', false, 'https://plaid.com')
ON CONFLICT DO NOTHING;
```

#### 1.6 Create Migration Script
- [ ] Create `migrations/001_plaid_schema_updates.sql` with all changes
- [ ] Create rollback script `migrations/001_plaid_schema_updates_rollback.sql`
- [ ] Test migration on local Docker database
- [ ] Document migration steps in README

#### 1.7 Update Supabase (if using Supabase hosted)
- [ ] Apply migrations to Supabase project
- [ ] Verify schema changes in Supabase dashboard
- [ ] Update RLS (Row Level Security) policies if needed

**Deliverables:**
- ✅ Updated schema supporting Plaid fields
- ✅ Migration scripts (forward + rollback)
- ✅ Schema documented
- ✅ All tests passing after migration

---

## Phase 2: Core Data Models & Database Layer (Week 2, Days 1-3)

### Goals
- Define unified Pydantic models
- Create database service layer
- Implement CRUD operations

### Tasks

#### 2.1 Define Unified Models
**File: `app/models/enums.py`**
- [ ] Create enums for:
  - `AccountType` (depository, credit, loan, investment)
  - `AccountSubtype` (checking, savings, credit_card, etc.)
  - `TransactionDirection` (Credit, Debit, Unknown)
  - `ConnectionStatus` (Initializing, Pending, Active, Needs_Reauth, Error, Revoked)
  - `AccountStatus` (Active, Pending, Completed, Expired, Failed)

**File: `app/models/connection.py`**
- [ ] Create `Connection` Pydantic model matching DB schema
- [ ] Add validation rules

**File: `app/models/account.py`**
- [ ] Create `UnifiedAccount` model (provider-agnostic)
- [ ] Add computed properties if needed

**File: `app/models/transaction.py`**
- [ ] Create `UnifiedTransaction` model
- [ ] Add validation for amount, dates, etc.

#### 2.2 Database Service Layer
**File: `app/core/database.py`**
- [ ] Set up Supabase client
- [ ] Create connection pool configuration
- [ ] Add helper methods for common queries

**File: `app/services/connection_service.py`**
```python
# Key methods to implement:
- create_connection(user_id, provider_id) -> Connection
- get_connection(connection_id) -> Connection
- get_user_connections(user_id) -> List[Connection]
- update_connection_status(connection_id, status)
- mark_needs_reauth(external_item_id)
- delete_connection(connection_id)
```

**File: `app/services/account_service.py`**
```python
# Key methods to implement:
- create_account(account: UnifiedAccount) -> Account
- get_account(account_id) -> Account
- get_user_accounts(user_id) -> List[Account]
- get_accounts_by_connection(connection_id) -> List[Account]
- update_account_balance(account_id, balances)
- delete_account(account_id)
- upsert_accounts(accounts: List[UnifiedAccount])  # For bulk sync
```

**File: `app/services/transaction_service.py`**
```python
# Key methods to implement:
- create_transaction(transaction: UnifiedTransaction) -> Transaction
- get_transaction(transaction_id) -> Transaction
- get_account_transactions(account_id, filters) -> List[Transaction]
- upsert_transactions(transactions: List[UnifiedTransaction])
- update_transaction(external_txn_id, updates)
- delete_transaction(external_txn_id)
```

#### 2.3 Request/Response Schemas
**File: `app/schemas/connection.py`**
- [ ] Create `ConnectionCreate`, `ConnectionUpdate`, `ConnectionResponse` schemas

**File: `app/schemas/account.py`**
- [ ] Create `AccountResponse`, `AccountListResponse` schemas

**File: `app/schemas/transaction.py`**
- [ ] Create `TransactionResponse`, `TransactionListResponse`, `TransactionFilters` schemas

#### 2.4 Unit Tests
- [ ] Write tests for all service methods
- [ ] Mock Supabase client
- [ ] Test edge cases (null values, invalid data)

**Deliverables:**
- ✅ Complete data models with validation
- ✅ Database service layer with CRUD operations
- ✅ Unit tests passing (>80% coverage)

---

## Phase 3: Plaid Client & Normalization Layer (Week 2, Days 4-5 + Week 3, Days 1-2)

### Goals
- Integrate Plaid Python SDK
- Build Plaid client wrapper
- Implement normalization layer (Plaid → Unified models)

### Tasks

#### 3.1 Plaid Client Setup
**File: `app/providers/plaid/client.py`**

```python
# Implement PlaidClient class with methods:

class PlaidClient:
    def __init__(self, client_id, secret, environment):
        # Initialize Plaid API client
        pass

    # Link Token Management
    async def create_link_token(self, user_id: str, products: List[str]) -> dict:
        """Create link token for Plaid Link"""
        pass

    # Token Exchange
    async def exchange_public_token(self, public_token: str) -> dict:
        """Exchange public_token for access_token"""
        pass

    # Accounts
    async def get_accounts(self, access_token: str) -> dict:
        """Fetch accounts for an item"""
        pass

    # Transactions
    async def sync_transactions(
        self,
        access_token: str,
        cursor: Optional[str] = None
    ) -> dict:
        """Sync transactions using /transactions/sync"""
        pass

    # Item Management
    async def get_item(self, access_token: str) -> dict:
        """Get item details"""
        pass

    async def remove_item(self, access_token: str) -> dict:
        """Remove item (disconnect)"""
        pass

    # Webhooks
    async def verify_webhook(self, webhook_body: bytes, signature: str) -> bool:
        """Verify Plaid webhook signature"""
        pass
```

**Tasks:**
- [ ] Implement all client methods
- [ ] Add error handling (Plaid-specific exceptions)
- [ ] Add retry logic with exponential backoff
- [ ] Add logging for all API calls
- [ ] Test all methods against Plaid sandbox

#### 3.2 Plaid-Specific Models
**File: `app/providers/plaid/models.py`**
- [ ] Create Pydantic models for Plaid API responses:
  - `PlaidAccount`
  - `PlaidTransaction`
  - `PlaidBalance`
  - `PlaidItem`
  - `PlaidLinkTokenResponse`
  - `PlaidWebhookPayload`

#### 3.3 Normalization Layer - Accounts
**File: `app/providers/plaid/normalizer.py`**

```python
class PlaidAccountNormalizer:
    @staticmethod
    def normalize(plaid_account: dict, user_id: str, connection_id: str) -> UnifiedAccount:
        """
        Map Plaid account to UnifiedAccount model

        Plaid account structure:
        {
            "account_id": "blgvvBlXw3cq5GMPwqB6s6q4dLKB9WcVqGDGo",
            "balances": {
                "available": 100.00,
                "current": 110.00,
                "limit": null,
                "iso_currency_code": "USD",
                "last_updated_datetime": "2024-01-15T14:30:00Z"
            },
            "mask": "0000",
            "name": "Plaid Checking",
            "official_name": "Plaid Gold Standard 0% Interest Checking",
            "type": "depository",
            "subtype": "checking",
            "verification_status": "automatically_verified",
            "persistent_account_id": "persistent_id_123",
            "holder_category": "personal"
        }
        """
        return UnifiedAccount(
            user_id=user_id,
            external_account_id=plaid_account["account_id"],
            name=plaid_account["name"],
            official_name=plaid_account.get("official_name"),
            account_type=plaid_account["type"],
            account_subtype=plaid_account.get("subtype"),
            currency=plaid_account["balances"]["iso_currency_code"] or "USD",
            mask=plaid_account.get("mask"),
            current_balance=plaid_account["balances"]["current"],
            available_balance=plaid_account["balances"].get("available"),
            credit_limit=plaid_account["balances"].get("limit"),
            institution_name=None,  # Will be set from connection
            verification_status=plaid_account.get("verification_status"),
            holder_category=plaid_account.get("holder_category"),
            provider_metadata={
                "plaid": {
                    "persistent_account_id": plaid_account.get("persistent_account_id"),
                    "last_updated_datetime": plaid_account["balances"].get("last_updated_datetime")
                }
            },
            account_status="Active",
            last_refreshed_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
```

**Tasks:**
- [ ] Implement `PlaidAccountNormalizer.normalize()`
- [ ] Handle all edge cases (missing fields, null values)
- [ ] Write unit tests with sample Plaid responses

#### 3.4 Normalization Layer - Transactions
**File: `app/providers/plaid/normalizer.py` (continued)**

```python
class PlaidTransactionNormalizer:
    @staticmethod
    def normalize(plaid_txn: dict, account_id: int) -> UnifiedTransaction:
        """
        Map Plaid transaction to UnifiedTransaction model

        Plaid transaction structure:
        {
            "account_id": "vzeNDwK7KQIm4yEog683uElbp9GRLEFXGK98D",
            "amount": 25.00,
            "iso_currency_code": "USD",
            "category": ["Food and Drink", "Restaurants"],
            "category_id": "13005000",
            "date": "2025-01-14",
            "authorized_date": "2025-01-14",
            "name": "Starbucks",
            "merchant_name": "Starbucks",
            "logo_url": "https://plaid-merchant-logos.plaid.com/starbucks_619.png",
            "website": "starbucks.com",
            "payment_channel": "in store",
            "pending": false,
            "transaction_id": "yBVBEwrXdDf9gfXP4kcKFK6FjqqmRhQ4JqYnb",
            "personal_finance_category": {
                "primary": "FOOD_AND_DRINK",
                "detailed": "FOOD_AND_DRINK_COFFEE",
                "confidence_level": "VERY_HIGH"
            },
            "counterparties": [...]
        }
        """
        # Plaid: positive amount = money out, negative = money in
        txn_direction = "Debit" if plaid_txn["amount"] > 0 else "Credit"

        return UnifiedTransaction(
            account_id=account_id,
            external_txn_id=plaid_txn["transaction_id"],
            txn_date=plaid_txn["date"],
            posted_at=plaid_txn["date"],
            authorized_date=plaid_txn.get("authorized_date"),
            amount=abs(plaid_txn["amount"]),  # Store as positive
            currency=plaid_txn.get("iso_currency_code", "USD"),
            txn_direction=txn_direction,
            description_raw=plaid_txn["name"],
            merchant_name_raw=plaid_txn.get("merchant_name"),
            merchant_logo_url=plaid_txn.get("logo_url"),
            merchant_website=plaid_txn.get("website"),
            pending=plaid_txn["pending"],
            category=" > ".join(plaid_txn.get("category", [])) if plaid_txn.get("category") else None,
            personal_finance_category=plaid_txn.get("personal_finance_category"),
            payment_channel=plaid_txn.get("payment_channel"),
            counterparties=plaid_txn.get("counterparties", []),
            location=plaid_txn.get("location"),
            provider_metadata={
                "plaid": {
                    "transaction_code": plaid_txn.get("transaction_code"),
                    "transaction_type": plaid_txn.get("transaction_type"),
                    "merchant_entity_id": plaid_txn.get("merchant_entity_id"),
                    "check_number": plaid_txn.get("check_number")
                }
            },
            raw_payload=plaid_txn
        )
```

**Tasks:**
- [ ] Implement `PlaidTransactionNormalizer.normalize()`
- [ ] Handle amount sign conversion (Plaid positive = debit)
- [ ] Test with various transaction types (purchase, refund, transfer, etc.)

#### 3.5 Integration Tests
- [ ] Test Plaid client against sandbox with real API calls
- [ ] Test normalization with sample Plaid responses
- [ ] Verify all fields map correctly

**Deliverables:**
- ✅ Complete Plaid client wrapper
- ✅ Normalization layer (Plaid → Unified models)
- ✅ Unit + integration tests passing

---

## Phase 4: Plaid Link Flow (Frontend-Backend Integration) (Week 3, Days 3-5)

### Goals
- Implement Plaid Link token creation
- Handle public token exchange
- Store connection in database

### Tasks

#### 4.1 Link Token Creation Endpoint
**File: `app/api/v1/connections.py`**

```python
@router.post("/plaid/link/token", response_model=LinkTokenResponse)
async def create_plaid_link_token(
    current_user: User = Depends(get_current_user)
):
    """
    Step 1: Create Plaid link_token for frontend

    Flow:
    1. Call Plaid API to create link_token
    2. Store initial connection record (status: Initializing)
    3. Return link_token to frontend
    """
    # Implementation here
    pass
```

**Tasks:**
- [ ] Implement link token creation
- [ ] Call Plaid `/link/token/create` API
- [ ] Insert initial connection record in DB
- [ ] Store link_token in connection.artifact
- [ ] Return link_token to frontend

#### 4.2 Public Token Exchange Endpoint
**File: `app/api/v1/connections.py`**

```python
@router.post("/plaid/exchange-token", response_model=ConnectionResponse)
async def exchange_plaid_public_token(
    request: ExchangeTokenRequest,  # { public_token, metadata }
    current_user: User = Depends(get_current_user)
):
    """
    Step 2: Exchange public_token for access_token

    Flow:
    1. Call Plaid /item/public_token/exchange
    2. Update connection with access_token & external_item_id
    3. Store institution info from metadata
    4. Update status to Pending
    5. Trigger account fetch in background
    """
    # Implementation here
    pass
```

**Tasks:**
- [ ] Implement token exchange endpoint
- [ ] Call Plaid `/item/public_token/exchange`
- [ ] Update connection record with:
  - `access_token`
  - `external_item_id`
  - `institution_id`
  - `institution_name`
  - `connection_status = 'Pending'`
- [ ] Trigger background job to fetch accounts

#### 4.3 Connection Status Endpoint
**File: `app/api/v1/connections.py`**

```python
@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get connection details"""
    pass

@router.get("/connections", response_model=List[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user)
):
    """List all user connections"""
    pass

@router.delete("/connections/{connection_id}")
async def disconnect(
    connection_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Disconnect Plaid item
    1. Call Plaid /item/remove
    2. Update connection status to Revoked
    3. Optionally: soft-delete accounts & transactions
    """
    pass
```

**Tasks:**
- [ ] Implement get connection endpoint
- [ ] Implement list connections endpoint
- [ ] Implement disconnect endpoint
- [ ] Add proper error handling and validation

#### 4.4 Complete Link Flow Service
**File: `app/services/connection_service.py`**

```python
class ConnectionService:
    async def create_plaid_connection(self, user_id: str) -> dict:
        """Create link token and initial connection"""
        # 1. Get Plaid provider_id
        # 2. Call Plaid client to create link_token
        # 3. Insert connection record (status: Initializing)
        # 4. Return link_token
        pass

    async def complete_plaid_connection(
        self,
        user_id: str,
        public_token: str,
        metadata: dict
    ) -> Connection:
        """Exchange token and complete connection"""
        # 1. Exchange public_token
        # 2. Update connection with access_token, item_id
        # 3. Update institution info
        # 4. Change status to Pending
        # 5. Return connection
        pass

    async def disconnect_plaid(self, connection_id: str):
        """Remove Plaid item"""
        # 1. Get connection
        # 2. Call Plaid /item/remove
        # 3. Update status to Revoked
        pass
```

**Deliverables:**
- ✅ Link token creation API
- ✅ Public token exchange API
- ✅ Connection management endpoints
- ✅ Integration tests for full link flow

---

## Phase 5: Data Sync - Accounts & Transactions (Week 4, Days 1-3)

### Goals
- Implement account sync from Plaid
- Implement transaction sync from Plaid
- Handle incremental updates

### Tasks

#### 5.1 Account Sync Service
**File: `app/services/sync_service.py`**

```python
class SyncService:
    async def sync_accounts(self, connection_id: str):
        """
        Sync accounts for a connection

        Flow:
        1. Get connection (access_token)
        2. Call Plaid /accounts/get
        3. Normalize accounts (Plaid → Unified)
        4. Upsert accounts to database
        5. Update connection products & status
        6. Update last_synced_at
        """
        connection = await connection_service.get_connection(connection_id)

        # Fetch from Plaid
        plaid_response = await plaid_client.get_accounts(connection.access_token)

        # Normalize accounts
        accounts = [
            PlaidAccountNormalizer.normalize(
                acc,
                connection.user_id,
                connection_id
            )
            for acc in plaid_response["accounts"]
        ]

        # Upsert to DB
        await account_service.upsert_accounts(accounts)

        # Update connection with item info
        await connection_service.update_connection(
            connection_id,
            {
                "products": plaid_response["item"]["billed_products"],
                "available_products": plaid_response["item"]["available_products"],
                "connection_status": "Active",
                "last_synced_at": datetime.utcnow()
            }
        )
```

**Tasks:**
- [ ] Implement `sync_accounts()` method
- [ ] Add error handling for Plaid API errors
- [ ] Handle account updates (balance changes)
- [ ] Handle account deletions (if any)
- [ ] Test with sandbox accounts

#### 5.2 Transaction Sync Service - Initial Sync
**File: `app/services/sync_service.py` (continued)**

```python
async def sync_transactions_initial(self, connection_id: str):
    """
    Initial transaction sync (no cursor)

    Flow:
    1. Get connection & accounts
    2. Call Plaid /transactions/sync (no cursor)
    3. Normalize transactions
    4. Insert transactions to DB
    5. Store next_cursor in connection.artifact
    """
    connection = await connection_service.get_connection(connection_id)
    accounts = await account_service.get_accounts_by_connection(connection_id)

    # Create account_id mapping (external_id → internal_id)
    account_map = {acc.external_account_id: acc.account_id for acc in accounts}

    # Fetch from Plaid
    plaid_response = await plaid_client.sync_transactions(
        connection.access_token,
        cursor=None  # Initial sync
    )

    # Process added transactions
    transactions = []
    for plaid_txn in plaid_response["added"]:
        account_id = account_map.get(plaid_txn["account_id"])
        if account_id:
            txn = PlaidTransactionNormalizer.normalize(plaid_txn, account_id)
            transactions.append(txn)

    # Insert to DB
    await transaction_service.upsert_transactions(transactions)

    # Store cursor
    await connection_service.update_artifact(
        connection_id,
        {"transactions_cursor": plaid_response["next_cursor"]}
    )
```

**Tasks:**
- [ ] Implement `sync_transactions_initial()`
- [ ] Handle account mapping (external → internal IDs)
- [ ] Test with sandbox transactions

#### 5.3 Transaction Sync Service - Incremental Sync
**File: `app/services/sync_service.py` (continued)**

```python
async def sync_transactions_incremental(self, connection_id: str):
    """
    Incremental transaction sync (with cursor)

    Handles:
    - added: New transactions → INSERT
    - modified: Updated transactions → UPDATE
    - removed: Deleted transactions → DELETE
    """
    connection = await connection_service.get_connection(connection_id)
    cursor = connection.artifact.get("transactions_cursor")

    accounts = await account_service.get_accounts_by_connection(connection_id)
    account_map = {acc.external_account_id: acc.account_id for acc in accounts}

    # Fetch from Plaid with cursor
    plaid_response = await plaid_client.sync_transactions(
        connection.access_token,
        cursor=cursor
    )

    # Handle ADDED
    for plaid_txn in plaid_response["added"]:
        account_id = account_map.get(plaid_txn["account_id"])
        if account_id:
            txn = PlaidTransactionNormalizer.normalize(plaid_txn, account_id)
            await transaction_service.upsert_transaction(txn)

    # Handle MODIFIED
    for plaid_txn in plaid_response["modified"]:
        account_id = account_map.get(plaid_txn["account_id"])
        if account_id:
            txn = PlaidTransactionNormalizer.normalize(plaid_txn, account_id)
            await transaction_service.update_transaction(
                txn.external_txn_id,
                txn
            )

    # Handle REMOVED
    for removed_txn in plaid_response["removed"]:
        await transaction_service.delete_transaction(
            removed_txn["transaction_id"]
        )

    # Update cursor
    await connection_service.update_artifact(
        connection_id,
        {"transactions_cursor": plaid_response["next_cursor"]}
    )

    # Update last_synced_at
    await connection_service.update_last_synced(connection_id)
```

**Tasks:**
- [ ] Implement `sync_transactions_incremental()`
- [ ] Handle added, modified, removed transactions
- [ ] Update cursor after each sync
- [ ] Test with sandbox (simulate updates)

#### 5.4 Complete Sync Orchestration
**File: `app/services/sync_service.py` (continued)**

```python
async def sync_connection(self, connection_id: str):
    """
    Complete sync for a connection
    1. Sync accounts (always)
    2. Sync transactions (initial or incremental)
    """
    try:
        # Sync accounts
        await self.sync_accounts(connection_id)

        # Check if initial or incremental sync
        connection = await connection_service.get_connection(connection_id)
        cursor = connection.artifact.get("transactions_cursor")

        if cursor:
            await self.sync_transactions_incremental(connection_id)
        else:
            await self.sync_transactions_initial(connection_id)

        logger.info(f"Sync completed for connection {connection_id}")

    except PlaidError as e:
        # Handle Plaid-specific errors
        if e.code == "ITEM_LOGIN_REQUIRED":
            await connection_service.mark_needs_reauth(connection_id)
        else:
            logger.error(f"Plaid error: {e}")
            raise

    except Exception as e:
        logger.error(f"Sync failed for {connection_id}: {e}")
        raise
```

**Deliverables:**
- ✅ Account sync implementation
- ✅ Transaction sync (initial + incremental)
- ✅ Complete sync orchestration
- ✅ Error handling for common scenarios

---

## Phase 6: Webhooks & Real-time Sync (Week 4, Days 4-5)

### Goals
- Implement Plaid webhook receiver
- Handle webhook events
- Trigger real-time syncs

### Tasks

#### 6.1 Webhook Verification
**File: `app/providers/plaid/webhooks.py`**

```python
async def verify_plaid_webhook(
    request: Request,
    plaid_verification_key: str
) -> dict:
    """
    Verify Plaid webhook signature
    https://plaid.com/docs/api/webhooks/#webhook-verification
    """
    body = await request.body()
    signature = request.headers.get("Plaid-Verification")

    # Verify signature using JWT
    # Implementation here

    return await request.json()
```

**Tasks:**
- [ ] Implement webhook signature verification
- [ ] Handle signature validation failures

#### 6.2 Webhook Handler Endpoint
**File: `app/api/v1/webhooks.py`**

```python
@router.post("/plaid/webhook")
async def plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Plaid webhook receiver

    Webhook types:
    - TRANSACTIONS.DEFAULT_UPDATE: New transactions available
    - ITEM.ERROR: Item error (needs reauth)
    - ITEM.PENDING_EXPIRATION: Consent expiring soon
    - ITEM.USER_PERMISSION_REVOKED: User revoked access
    """
    # Verify webhook
    webhook = await verify_plaid_webhook(request, settings.PLAID_WEBHOOK_KEY)

    webhook_type = webhook.get("webhook_type")
    webhook_code = webhook.get("webhook_code")
    item_id = webhook.get("item_id")

    # Get connection
    connection = await connection_service.get_by_item_id(item_id)

    # Handle different webhook types
    if webhook_type == "TRANSACTIONS":
        if webhook_code == "DEFAULT_UPDATE":
            # New transactions available - trigger sync
            background_tasks.add_task(
                sync_service.sync_transactions_incremental,
                connection.connection_id
            )

        elif webhook_code == "INITIAL_UPDATE":
            # Initial transaction data ready
            background_tasks.add_task(
                sync_service.sync_transactions_initial,
                connection.connection_id
            )

    elif webhook_type == "ITEM":
        if webhook_code == "ERROR":
            error_code = webhook["error"]["error_code"]

            if error_code == "ITEM_LOGIN_REQUIRED":
                # Mark connection as needs reauth
                await connection_service.update_connection(
                    connection.connection_id,
                    {
                        "connection_status": "Needs_Reauth",
                        "error_code": error_code,
                        "error_message": webhook["error"]["error_message"]
                    }
                )

        elif webhook_code == "PENDING_EXPIRATION":
            # TODO: Notify user to re-link
            pass

        elif webhook_code == "USER_PERMISSION_REVOKED":
            # User revoked at bank level
            await connection_service.update_connection(
                connection.connection_id,
                {
                    "connection_status": "Revoked",
                    "revoked_at": datetime.utcnow(),
                    "revocation_reason": "User revoked at institution"
                }
            )

    return {"status": "received"}
```

**Tasks:**
- [ ] Implement webhook handler for all event types
- [ ] Add webhook signature verification
- [ ] Trigger appropriate sync jobs
- [ ] Update connection status based on events
- [ ] Log all webhook events

#### 6.3 Webhook Configuration
- [ ] Configure webhook URL in Plaid dashboard
- [ ] Use ngrok for local testing
- [ ] Test with Plaid sandbox webhooks
- [ ] Document webhook setup for production

**Deliverables:**
- ✅ Webhook receiver endpoint
- ✅ Event handlers for all webhook types
- ✅ Real-time sync triggered by webhooks
- ✅ Webhook verification implemented

---

## Phase 7: Background Jobs & Scheduled Sync (Week 5, Days 1-2)

### Goals
- Set up APScheduler
- Implement scheduled sync jobs
- Add job monitoring

### Tasks

#### 7.1 Scheduler Setup
**File: `app/core/scheduler.py`**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Initialize and start scheduler"""
    scheduler.start()
    logger.info("Scheduler started")

def shutdown_scheduler():
    """Gracefully shutdown scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
```

**File: `app/main.py`**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)
```

**Tasks:**
- [ ] Set up AsyncIOScheduler
- [ ] Integrate with FastAPI lifecycle
- [ ] Add graceful shutdown

#### 7.2 Scheduled Sync Jobs
**File: `app/tasks/scheduled.py`**

```python
from app.core.scheduler import scheduler

async def sync_all_active_connections():
    """
    Daily batch sync for all active connections
    Runs at 2 AM daily (fallback for missed webhooks)
    """
    logger.info("Starting daily batch sync")

    connections = await connection_service.get_connections(
        provider="plaid",
        status="Active"
    )

    for connection in connections:
        try:
            await sync_service.sync_connection(connection.connection_id)
            logger.info(f"Synced connection {connection.connection_id}")
        except Exception as e:
            logger.error(f"Failed to sync {connection.connection_id}: {e}")
            # Don't fail entire batch if one connection fails

async def check_connection_health():
    """
    Check for stale connections (not synced in 48h)
    Runs every 6 hours
    """
    logger.info("Checking connection health")

    stale_threshold = datetime.utcnow() - timedelta(hours=48)

    connections = await connection_service.get_connections(
        status="Active",
        last_synced_before=stale_threshold
    )

    for connection in connections:
        logger.warning(f"Stale connection: {connection.connection_id}")
        # TODO: Trigger manual sync or notify user

# Schedule jobs
scheduler.add_job(
    sync_all_active_connections,
    trigger=CronTrigger(hour=2, minute=0),
    id="daily_batch_sync",
    replace_existing=True,
    max_instances=1  # Prevent overlapping runs
)

scheduler.add_job(
    check_connection_health,
    trigger=IntervalTrigger(hours=6),
    id="connection_health_check",
    replace_existing=True
)
```

**Tasks:**
- [ ] Implement daily batch sync
- [ ] Implement connection health check
- [ ] Add job monitoring/logging
- [ ] Test scheduler with different triggers

#### 7.3 Manual Sync Endpoint
**File: `app/api/v1/connections.py`**

```python
@router.post("/connections/{connection_id}/sync")
async def trigger_manual_sync(
    connection_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    User-initiated sync (refresh button)
    """
    # Verify user owns connection
    connection = await connection_service.get_connection(connection_id)
    if connection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Trigger sync in background
    background_tasks.add_task(
        sync_service.sync_connection,
        connection_id
    )

    return {"status": "sync_started"}
```

**Deliverables:**
- ✅ APScheduler configured and running
- ✅ Daily batch sync job
- ✅ Connection health monitoring
- ✅ Manual sync endpoint

---

## Phase 8: Error Handling & Monitoring (Week 5, Days 3-4)

### Goals
- Implement comprehensive error handling
- Add logging and monitoring
- Set up Sentry for error tracking

### Tasks

#### 8.1 Error Handling
**File: `app/utils/exceptions.py`**

```python
class PlaidIntegrationError(Exception):
    """Base exception for Plaid integration"""
    pass

class PlaidAPIError(PlaidIntegrationError):
    """Plaid API returned an error"""
    def __init__(self, error_code: str, error_message: str):
        self.error_code = error_code
        self.error_message = error_message

class ConnectionNotFoundError(PlaidIntegrationError):
    """Connection not found"""
    pass

class SyncError(PlaidIntegrationError):
    """Error during sync"""
    pass
```

**File: `app/main.py`**
```python
@app.exception_handler(PlaidAPIError)
async def plaid_error_handler(request: Request, exc: PlaidAPIError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "plaid_error",
            "code": exc.error_code,
            "message": exc.error_message
        }
    )
```

**Tasks:**
- [ ] Create custom exception classes
- [ ] Add exception handlers to FastAPI
- [ ] Handle common Plaid errors:
  - `ITEM_LOGIN_REQUIRED`
  - `RATE_LIMIT_EXCEEDED`
  - `INVALID_ACCESS_TOKEN`
  - `ITEM_LOCKED`

#### 8.2 Logging
**File: `app/utils/logger.py`**

```python
from loguru import logger
import sys

def setup_logger():
    # Remove default handler
    logger.remove()

    # Add custom handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # Add file handler
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG"
    )
```

**Tasks:**
- [ ] Set up Loguru logger
- [ ] Add structured logging
- [ ] Log all Plaid API calls
- [ ] Log sync job execution
- [ ] Add correlation IDs for tracing

#### 8.3 Sentry Integration
**File: `app/main.py`**

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT
    )
```

**Tasks:**
- [ ] Set up Sentry project
- [ ] Add Sentry SDK to FastAPI
- [ ] Configure error tracking
- [ ] Test error reporting

#### 8.4 Retry Logic
**File: `app/utils/retry.py`**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def retry_plaid_call(func, *args, **kwargs):
    """Retry Plaid API calls with exponential backoff"""
    return await func(*args, **kwargs)
```

**Tasks:**
- [ ] Implement retry decorator
- [ ] Apply to Plaid API calls
- [ ] Configure retry policy

**Deliverables:**
- ✅ Comprehensive error handling
- ✅ Structured logging with Loguru
- ✅ Sentry error tracking configured
- ✅ Retry logic for API calls

---

## Phase 9: API Documentation & Testing (Week 5, Day 5 + Week 6, Days 1-2)

### Goals
- Document all APIs with OpenAPI
- Write comprehensive tests
- Create Postman collection

### Tasks

#### 9.1 API Documentation
**File: `app/main.py`**

```python
app = FastAPI(
    title="Nidhi Expense App - Plaid Integration",
    description="API for managing Plaid connections and syncing financial data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
```

**Tasks:**
- [ ] Add docstrings to all endpoints
- [ ] Define response models
- [ ] Add example requests/responses
- [ ] Review auto-generated OpenAPI docs
- [ ] Export OpenAPI spec

#### 9.2 Unit Tests
**File: `tests/unit/test_normalizers.py`**
- [ ] Test PlaidAccountNormalizer with various inputs
- [ ] Test PlaidTransactionNormalizer
- [ ] Test edge cases (missing fields, null values)

**File: `tests/unit/test_services.py`**
- [ ] Test connection_service methods
- [ ] Test account_service methods
- [ ] Test transaction_service methods
- [ ] Test sync_service orchestration
- [ ] Mock Supabase client

#### 9.3 Integration Tests
**File: `tests/integration/test_plaid_flow.py`**
- [ ] Test complete link flow (create token → exchange → sync)
- [ ] Test account sync
- [ ] Test transaction sync (initial + incremental)
- [ ] Test webhook handling
- [ ] Use Plaid sandbox

#### 9.4 End-to-End Tests
- [ ] Test full user journey:
  1. Create link token
  2. Exchange public token
  3. Sync accounts
  4. Sync transactions
  5. View data
  6. Disconnect

#### 9.5 Postman Collection
- [ ] Create Postman collection with all endpoints
- [ ] Add environment variables (dev, staging, prod)
- [ ] Add tests in Postman
- [ ] Export collection

**Deliverables:**
- ✅ API documentation (OpenAPI/Swagger)
- ✅ Unit tests (>80% coverage)
- ✅ Integration tests
- ✅ Postman collection

---

## Phase 10: Deployment & Production Readiness (Week 6, Days 3-5)

### Goals
- Prepare for production deployment
- Configure environment variables
- Set up CI/CD

### Tasks

#### 10.1 Environment Configuration
**File: `.env.example`**
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Plaid
PLAID_CLIENT_ID=your-client-id
PLAID_SECRET=your-secret
PLAID_ENV=sandbox  # sandbox, development, production
PLAID_WEBHOOK_URL=https://your-api.com/api/v1/webhooks/plaid
PLAID_WEBHOOK_VERIFICATION_KEY=your-webhook-key

# Security
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Sentry
SENTRY_DSN=your-sentry-dsn
ENVIRONMENT=production

# App
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

**Tasks:**
- [ ] Create `.env.example` with all required variables
- [ ] Document environment variables in README
- [ ] Set up secrets management (production)

#### 10.2 Docker Configuration
**File: `Dockerfile`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy app
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Tasks:**
- [ ] Create Dockerfile
- [ ] Create docker-compose.yml
- [ ] Test local Docker build
- [ ] Optimize Docker image size

#### 10.3 Deployment
**Deployment Options:**

**Option 1: Railway (Recommended for MVP)**
- [ ] Create Railway account
- [ ] Connect GitHub repo
- [ ] Configure environment variables
- [ ] Deploy
- [ ] Set up custom domain

**Option 2: Render**
- [ ] Create Render account
- [ ] Create web service
- [ ] Configure build & start commands
- [ ] Add environment variables
- [ ] Deploy

**Option 3: AWS ECS / DigitalOcean (Production)**
- [ ] Set up container registry
- [ ] Configure load balancer
- [ ] Set up auto-scaling
- [ ] Configure monitoring

#### 10.4 CI/CD
**File: `.github/workflows/test.yml`**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run tests
        run: poetry run pytest
```

**Tasks:**
- [ ] Set up GitHub Actions
- [ ] Add test workflow
- [ ] Add lint workflow
- [ ] Add deployment workflow (optional)

#### 10.5 Production Checklist
- [ ] Switch Plaid to `development` or `production` environment
- [ ] Configure production webhook URL
- [ ] Set up database backups
- [ ] Enable HTTPS
- [ ] Configure CORS
- [ ] Set up rate limiting
- [ ] Enable authentication
- [ ] Set up monitoring dashboard
- [ ] Create runbook for common issues

**Deliverables:**
- ✅ Dockerized application
- ✅ Deployed to production
- ✅ CI/CD pipeline configured
- ✅ Production monitoring enabled

---

## Phase 11: Documentation & Handoff (Week 6, Ongoing)

### Goals
- Create comprehensive documentation
- Document architecture decisions
- Create operational guides

### Tasks

#### 11.1 README Documentation
**File: `README.md`**

Sections to include:
- [ ] Project overview
- [ ] Architecture diagram
- [ ] Tech stack
- [ ] Getting started (local setup)
- [ ] Environment variables
- [ ] Running tests
- [ ] Deployment guide
- [ ] API documentation link
- [ ] Troubleshooting

#### 11.2 Architecture Documentation
**File: `docs/ARCHITECTURE.md`**
- [ ] System architecture diagram
- [ ] Data flow diagrams (Plaid Link flow, Sync flow)
- [ ] Database schema
- [ ] Provider normalization strategy

#### 11.3 Operational Runbook
**File: `docs/RUNBOOK.md`**
- [ ] How to handle common errors
- [ ] How to manually trigger sync
- [ ] How to reconnect failed connections
- [ ] How to monitor system health
- [ ] Plaid webhook troubleshooting

#### 11.4 Developer Guide
**File: `docs/DEVELOPER_GUIDE.md`**
- [ ] Code structure explanation
- [ ] How to add new endpoints
- [ ] How to add new providers (future)
- [ ] Testing guidelines
- [ ] Contribution guidelines

**Deliverables:**
- ✅ Complete README
- ✅ Architecture documentation
- ✅ Operational runbook
- ✅ Developer guide

---

## Testing Strategy

### Unit Tests
- All normalizers (Plaid → Unified)
- All service methods
- Mock external dependencies

### Integration Tests
- Plaid client methods (against sandbox)
- Database operations
- Sync orchestration

### End-to-End Tests
- Complete Plaid Link flow
- Account sync
- Transaction sync
- Webhook handling

### Performance Tests (Future)
- Load testing sync jobs
- Database query optimization
- API response times

---

## Key Metrics to Track

### Technical Metrics
- API response time (<200ms P95)
- Sync job duration (<30s per connection)
- Error rate (<1%)
- Test coverage (>80%)

### Business Metrics
- Successful connections rate
- Sync success rate
- Webhook processing time
- Average transactions per user

---

## Risk Mitigation

### Technical Risks
1. **Plaid API rate limits**
   - Mitigation: Implement retry logic, backoff strategy

2. **Database performance**
   - Mitigation: Add indexes, use connection pooling

3. **Webhook delivery failures**
   - Mitigation: Implement fallback batch sync

### Business Risks
1. **User connection failures**
   - Mitigation: Clear error messages, reauth flow

2. **Data sync issues**
   - Mitigation: Manual sync button, monitoring alerts

---

## Success Criteria

### Phase Completion
- [ ] All endpoints implemented and tested
- [ ] Plaid integration working in sandbox
- [ ] All tests passing (unit + integration)
- [ ] Documentation complete
- [ ] Deployed to production
- [ ] Monitoring enabled

### Production Readiness
- [ ] Handle 1000+ connections
- [ ] <200ms API response time
- [ ] >99% sync success rate
- [ ] Zero data loss
- [ ] Proper error handling and logging

---

## Next Steps After Plaid Integration

1. **Text2SQL System Integration** (Phase 12)
   - Update Text2SQL with new schema
   - Add support for Plaid-specific fields
   - Test queries on normalized data

2. **Analytics & Insights** (Phase 13)
   - Spending patterns
   - Category analysis
   - Budget tracking

3. **Multi-Provider Support** (Phase 14)
   - Add Setu AA integration
   - Abstract provider interface
   - Test provider switching

4. **Advanced Features** (Phase 15)
   - Transaction categorization (ML)
   - Duplicate detection
   - Budget alerts

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 0. Setup | 2 days | Project scaffolded, Plaid sandbox configured |
| 1. Schema | 3 days | Schema updated, migrations ready |
| 2. Models | 3 days | Data models, DB service layer |
| 3. Plaid Client | 4 days | Plaid client, normalization layer |
| 4. Link Flow | 3 days | Link token, exchange, connections |
| 5. Data Sync | 3 days | Accounts & transaction sync |
| 6. Webhooks | 2 days | Webhook receiver, event handlers |
| 7. Background Jobs | 2 days | Scheduler, batch sync |
| 8. Error Handling | 2 days | Errors, logging, monitoring |
| 9. Testing | 3 days | Unit, integration, E2E tests |
| 10. Deployment | 3 days | Docker, CI/CD, production deploy |
| 11. Documentation | Ongoing | README, runbook, guides |

**Total: ~6 weeks** (30 working days)

---

## Appendix

### Useful Resources
- Plaid API Docs: https://plaid.com/docs/
- Plaid Quickstart: https://plaid.com/docs/quickstart/
- Plaid Webhooks: https://plaid.com/docs/api/webhooks/
- Plaid Sandbox: https://plaid.com/docs/sandbox/
- FastAPI Docs: https://fastapi.tiangolo.com/
- Supabase Docs: https://supabase.com/docs

### Plaid Sandbox Credentials
- Use Plaid sandbox institutions (e.g., "First Platypus Bank")
- Default sandbox credentials: `user_good` / `pass_good`
- Test different scenarios with sandbox users

### Common Plaid Error Codes
- `ITEM_LOGIN_REQUIRED`: User needs to reauth
- `RATE_LIMIT_EXCEEDED`: Too many API calls
- `INVALID_ACCESS_TOKEN`: Token invalid/revoked
- `ITEM_LOCKED`: Institution locked the item

---

**Document Version**: 1.0
**Last Updated**: 2025-01-17
**Author**: Development Team
**Status**: Ready for Implementation
