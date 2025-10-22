"""
FastAPI application for fake bank onboarding
Provides REST API endpoints for bank selection, account generation, and transaction creation
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from banks_config import get_all_banks, get_bank_by_code
from fake_data_generator import FakeDataGenerator
from db_operations import DatabaseOperations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Nidhi-Fi Fake Bank Onboarding API",
    description="API for fake bank account onboarding with transaction generation",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
data_generator = FakeDataGenerator()
db_ops = DatabaseOperations()


# Pydantic models for request/response validation
class BankConnectRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    bank_code: str = Field(..., description="Bank code (e.g., 'chase', 'icici')")


class AccountSelectRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    account_ids: List[int] = Field(..., description="List of account IDs to select")


class AccountResponse(BaseModel):
    account_id: int
    name: str
    mask: Optional[str]
    account_type: str
    account_subtype: Optional[str]
    current_balance: float
    available_balance: Optional[float]
    credit_limit: Optional[float]
    currency: str


class BankConnectResponse(BaseModel):
    connection_id: str
    institution_name: str
    accounts_created: int
    accounts: List[AccountResponse]


class AccountSelectResponse(BaseModel):
    success: bool
    accounts_with_transactions: int
    total_transactions_created: int
    message: str


class AccountSummaryResponse(BaseModel):
    total_accounts: int
    total_balance: float
    accounts: List[dict]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Nidhi-Fi Fake Bank Onboarding API",
        "version": "1.0.0",
        "endpoints": {
            "banks": "/api/banks",
            "connect": "/api/banks/connect",
            "select": "/api/accounts/select",
            "summary": "/api/accounts/summary",
        },
    }


@app.get("/api/banks")
async def get_banks():
    """
    Get list of available banks organized by region

    Returns:
        - us_banks: List of US banks
        - indian_banks: List of Indian banks
    """
    try:
        banks = get_all_banks()
        return banks
    except Exception as e:
        logger.error(f"Error fetching banks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch banks: {str(e)}",
        )


@app.post("/api/banks/connect", response_model=BankConnectResponse)
async def connect_bank(request: BankConnectRequest):
    """
    Connect a bank and generate fake accounts

    Process:
    1. Validate bank code
    2. Create/get provider
    3. Create connection
    4. Generate 10 accounts
    5. Store in database
    6. Return account list

    Args:
        request: BankConnectRequest with user_id and bank_code

    Returns:
        BankConnectResponse with connection details and generated accounts
    """
    try:
        # Validate bank code
        bank_config = get_bank_by_code(request.bank_code)
        if not bank_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bank code: {request.bank_code}",
            )

        logger.info(f"Connecting bank {bank_config['name']} for user {request.user_id}")

        # Check if user already has a connection for this bank
        existing_connection = db_ops.supabase.table("connections").select("connection_id, institution_id").eq("user_id", request.user_id).eq("institution_id", bank_config["institution_id"]).execute()

        if existing_connection.data and len(existing_connection.data) > 0:
            # Return existing connection and accounts
            connection_id = existing_connection.data[0]["connection_id"]
            logger.info(f"User already has connection {connection_id} for {bank_config['name']}")

            # Fetch existing accounts for this connection
            existing_accounts_response = db_ops.supabase.table("accounts").select("*").eq("user_id", request.user_id).eq("institution_name", bank_config["name"]).execute()

            created_accounts = []
            if existing_accounts_response.data:
                for account in existing_accounts_response.data:
                    created_accounts.append(
                        AccountResponse(
                            account_id=account["account_id"],
                            name=account["name"],
                            mask=account.get("mask"),
                            account_type=account["account_type"],
                            account_subtype=account.get("account_subtype"),
                            current_balance=account["current_balance"],
                            available_balance=account.get("available_balance"),
                            credit_limit=account.get("credit_limit"),
                            currency=account.get("currency", "USD"),
                        )
                    )

            return BankConnectResponse(
                connection_id=connection_id,
                institution_name=bank_config["name"],
                accounts_created=len(created_accounts),
                accounts=created_accounts,
            )

        # Step 1: Create or get provider
        provider_id = db_ops.create_or_get_provider()
        logger.info(f"Provider ID: {provider_id}")

        # Step 2: Generate connection data
        connection_data = data_generator.generate_connection_data(
            user_id=request.user_id,
            provider_id=provider_id,
            bank_code=request.bank_code,
        )

        # Step 3: Create connection
        connection_id = db_ops.create_connection(connection_data)
        logger.info(f"Created connection ID: {connection_id}")

        # Step 4: Generate 10 accounts
        accounts_data = data_generator.generate_accounts_for_bank(
            user_id=request.user_id, bank_code=request.bank_code, num_accounts=10
        )

        # Step 5: Store accounts in database (batch insert)
        account_ids = db_ops.create_accounts_batch(accounts_data)
        logger.info(f"Created {len(account_ids)} accounts")

        # Step 6: Fetch created accounts to return
        created_accounts = []
        for account_id in account_ids:
            account = db_ops.get_account_by_id(account_id)
            if account:
                created_accounts.append(
                    AccountResponse(
                        account_id=account["account_id"],
                        name=account["name"],
                        mask=account.get("mask"),
                        account_type=account["account_type"],
                        account_subtype=account.get("account_subtype"),
                        current_balance=account["current_balance"],
                        available_balance=account.get("available_balance"),
                        credit_limit=account.get("credit_limit"),
                        currency=account.get("currency", "USD"),
                    )
                )

        return BankConnectResponse(
            connection_id=connection_id,
            institution_name=bank_config["name"],
            accounts_created=len(created_accounts),
            accounts=created_accounts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting bank: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect bank: {str(e)}",
        )


@app.put("/api/users/{user_id}/onboarding-complete")
async def mark_onboarding_complete(user_id: str):
    """
    Mark user's onboarding as complete

    Args:
        user_id: User UUID

    Returns:
        Success status
    """
    try:
        # Update profiles table
        response = db_ops.supabase.table("profiles").update({
            "onboarding_complete": True
        }).eq("id", user_id).execute()

        if response.data:
            return {"success": True, "message": "Onboarding marked as complete"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except Exception as e:
        logger.error(f"Error marking onboarding complete: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update onboarding status: {str(e)}"
        )


@app.get("/api/users/{user_id}/onboarding-status")
async def get_onboarding_status(user_id: str):
    """
    Get user's onboarding status

    Args:
        user_id: User UUID

    Returns:
        Onboarding status
    """
    try:
        response = db_ops.supabase.table("profiles").select("onboarding_complete").eq("id", user_id).execute()

        if response.data and len(response.data) > 0:
            return {
                "onboarding_complete": response.data[0].get("onboarding_complete", False)
            }
        else:
            # User not found, return false by default
            return {"onboarding_complete": False}
    except Exception as e:
        logger.error(f"Error getting onboarding status: {str(e)}")
        # Return false by default on error
        return {"onboarding_complete": False}


@app.post("/api/accounts/select", response_model=AccountSelectResponse)
async def select_accounts(request: AccountSelectRequest):
    """
    Select accounts and generate transactions

    Process:
    1. Validate account ownership
    2. For each selected account:
       a. Generate 1000+ transactions
       b. Store in database
    3. Return success status

    Args:
        request: AccountSelectRequest with user_id and account_ids

    Returns:
        AccountSelectResponse with transaction generation summary
    """
    try:
        # Validate account IDs
        if not request.account_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one account must be selected",
            )

        logger.info(
            f"Selecting {len(request.account_ids)} accounts for user {request.user_id}"
        )

        # Verify account ownership
        if not db_ops.verify_accounts_ownership(request.account_ids, request.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="One or more accounts do not belong to this user",
            )

        total_transactions_created = 0

        # Generate transactions for each selected account
        for account_id in request.account_ids:
            logger.info(f"Generating transactions for account {account_id}")

            # Get account details
            account = db_ops.get_account_by_id(account_id)
            if not account:
                logger.warning(f"Account {account_id} not found, skipping")
                continue

            # Generate transactions
            transactions = data_generator.generate_transactions_for_account(
                account_id=account["account_id"],
                account_type=account["account_type"],
                account_subtype=account.get("account_subtype", "checking"),
                current_balance=account["current_balance"],
                currency=account.get("currency", "USD"),
                credit_limit=account.get("credit_limit"),
                num_transactions=1000,
            )

            logger.info(f"Generated {len(transactions)} transactions for account {account_id}")

            # Bulk insert transactions
            created_count = db_ops.bulk_create_transactions(transactions)
            total_transactions_created += created_count

            logger.info(f"Inserted {created_count} transactions for account {account_id}")

        # Mark onboarding as complete after successful transaction generation
        try:
            db_ops.supabase.table("profiles").update({
                "onboarding_complete": True
            }).eq("id", request.user_id).execute()
            logger.info(f"Marked onboarding complete for user {request.user_id}")
        except Exception as e:
            logger.warning(f"Failed to mark onboarding complete: {e}")
            # Don't fail the whole request if this fails

        return AccountSelectResponse(
            success=True,
            accounts_with_transactions=len(request.account_ids),
            total_transactions_created=total_transactions_created,
            message=f"Successfully generated {total_transactions_created} transactions for {len(request.account_ids)} accounts",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transactions: {str(e)}",
        )


@app.get("/api/accounts/summary", response_model=AccountSummaryResponse)
async def get_accounts_summary(user_id: str):
    """
    Get summary of user's accounts with transaction counts

    Args:
        user_id: User UUID (query parameter)

    Returns:
        AccountSummaryResponse with account summary
    """
    try:
        logger.info(f"Fetching account summary for user {user_id}")

        summary = db_ops.get_user_accounts_summary(user_id)

        return AccountSummaryResponse(
            total_accounts=summary["total_accounts"],
            total_balance=summary["total_balance"],
            accounts=summary["accounts"],
        )

    except Exception as e:
        logger.error(f"Error fetching account summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch account summary: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nidhi-fi-backend"}


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "detail": str(exc)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return {"error": "Internal server error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
