"""
FastAPI application for fake bank onboarding
Provides REST API endpoints for bank selection, account generation, and transaction creation
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from uuid import UUID
import logging
from decimal import Decimal
from datetime import datetime, date

from banks_config import get_all_banks, get_bank_by_code
from fake_data_generator import FakeDataGenerator
from db_operations import DatabaseOperations

# Import text2sql pipeline
from text2sql.core.pipeline import get_pipeline
from text2sql.cache import get_cache_manager

# Import conversation utilities
from conversation_utils import generate_conversation_title

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

# Initialize text2sql pipeline
try:
    text2sql_pipeline = get_pipeline()
    logger.info("✅ Text2SQL chatbot pipeline initialized")
except Exception as e:
    logger.warning(f"⚠️  Text2SQL initialization failed: {e}")
    text2sql_pipeline = None


# Pydantic models for request/response validation
class BankConnectRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    bank_code: str = Field(..., description="Bank code (e.g., 'chase', 'icici')")


class AccountSelectRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    account_ids: List[UUID] = Field(..., description="List of account UUIDs to select")


class AccountResponse(BaseModel):
    account_id: UUID
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


# Text2SQL Chatbot Models
class ChatQueryRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    query: str = Field(..., description="Natural language query", max_length=500)
    context: Optional[str] = Field(None, description="Additional context")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for multi-turn conversations")


class ChatQueryResponse(BaseModel):
    success: bool
    user_query: str
    generated_sql: Optional[str] = None
    results: Optional[List[dict]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time: float = 0
    natural_language_response: Optional[str] = None
    error: Optional[str] = None
    conversation_id: Optional[str] = None  # Added for conversation tracking


# Conversation Models
class ConversationCreateRequest(BaseModel):
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    title: Optional[str] = Field(None, description="Optional conversation title")


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., description="New title for the conversation")


class ConversationResponse(BaseModel):
    conversation_id: str
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    last_message_at: Optional[str]
    is_archived: bool
    message_count: Optional[int] = None


class ConversationListResponse(BaseModel):
    total: int
    conversations: List[ConversationResponse]


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    role: str
    content: str
    sql_query: Optional[str]
    query_results_summary: Optional[dict]
    execution_time: Optional[float]
    error: Optional[str]
    model_version: Optional[str]
    metadata: Optional[dict]
    created_at: str


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    total_messages: int
    messages: List[MessageResponse]


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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert an object to JSON-serializable format

    Handles:
    - Decimal -> float
    - datetime/date -> ISO format string
    - dict/list -> recursively convert values

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj


# ============================================================================
# TEXT2SQL CHATBOT ENDPOINTS
# ============================================================================

@app.post("/api/chat/query", response_model=ChatQueryResponse)
async def chat_query(request: ChatQueryRequest):
    """
    Text2SQL Chatbot endpoint with conversation storage

    Converts natural language queries to SQL, executes them, and stores conversation history

    Args:
        request: ChatQueryRequest with user_id, query, and optional conversation_id

    Returns:
        ChatQueryResponse with SQL, results, natural language response, and conversation_id
    """
    try:
        if not text2sql_pipeline:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Text2SQL chatbot is not available. OpenAI API key may be missing.",
            )

        logger.info(f"💬 Chat query from user {request.user_id}: '{request.query}'")

        # =====================================================================
        # Step 1: Get or create conversation
        # =====================================================================
        conversation_id = request.conversation_id
        is_new_conversation = False

        if not conversation_id:
            # Create new conversation
            try:
                conversation = db_ops.create_conversation(
                    user_id=request.user_id,
                    title=None  # Will be generated after processing
                )
                conversation_id = str(conversation["conversation_id"])
                is_new_conversation = True
                logger.info(f"✨ Created new conversation: {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to create conversation: {e}")
                # Continue without conversation storage
                conversation_id = None
        else:
            # Verify conversation exists and belongs to user
            conv = db_ops.get_conversation_by_id(conversation_id, request.user_id)
            if not conv:
                logger.warning(f"Conversation {conversation_id} not found or unauthorized")
                conversation_id = None

        # =====================================================================
        # Step 2: Get conversation context for follow-up questions
        # =====================================================================
        context_messages = ""
        if conversation_id and not is_new_conversation:
            try:
                last_messages = db_ops.get_last_n_messages(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    n=10  # Last 10 messages for context
                )
                # Build context from previous messages
                context_parts = []
                for msg in last_messages:
                    if msg["role"] == "user":
                        context_parts.append(f"User: {msg['content']}")
                    elif msg["role"] == "assistant" and msg.get("sql_query"):
                        context_parts.append(f"SQL: {msg['sql_query']}")
                context_messages = "\n".join(context_parts)
                logger.info(f"📜 Retrieved {len(last_messages)} messages for context")
            except Exception as e:
                logger.error(f"Failed to get conversation context: {e}")

        # Combine with provided context
        full_context = f"{context_messages}\n{request.context or ''}".strip()

        # =====================================================================
        # Step 3: Store user message
        # =====================================================================
        user_message_id = None
        if conversation_id:
            try:
                user_msg = db_ops.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=request.query,
                    metadata={"source": "chat_endpoint"}
                )
                user_message_id = str(user_msg["message_id"])
                logger.info(f"💾 Stored user message: {user_message_id}")
            except Exception as e:
                logger.error(f"Failed to store user message: {e}")

        # =====================================================================
        # Step 4: Process query through the pipeline
        # =====================================================================
        result = text2sql_pipeline.process_query(
            user_query=request.query,
            user_id=request.user_id,
            context=full_context,
            skip_validation=True  # Skip validation for faster responses
        )

        if not result['success']:
            logger.error(f"Pipeline failed: {result.get('error')}")

            # Store error message
            if conversation_id:
                try:
                    db_ops.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=result.get('error', 'Unknown error occurred'),
                        error=result.get('error'),
                        metadata={"error": True}
                    )
                except Exception as e:
                    logger.error(f"Failed to store error message: {e}")

            return ChatQueryResponse(
                success=False,
                user_query=request.query,
                error=result.get('error', 'Unknown error occurred'),
                conversation_id=conversation_id
            )

        # =====================================================================
        # Step 5: Format results
        # =====================================================================
        results_list = []
        query_result = result.get('query_result', {})
        if query_result.get('rows') and query_result.get('columns'):
            for row in query_result['rows']:
                row_dict = {}
                for i, col in enumerate(query_result['columns']):
                    # Convert to JSON-serializable format
                    row_dict[col] = make_json_serializable(row[i])
                results_list.append(row_dict)

        # =====================================================================
        # Step 6: Store assistant response
        # =====================================================================
        if conversation_id:
            try:
                # Create results summary (row_count + first 5 rows)
                results_summary = {
                    "row_count": query_result.get('row_count', 0),
                    "sample_rows": results_list[:5] if results_list else []
                }

                # Get cache hit info from result metadata
                cache_hit = result.get('metadata', {}).get('cache_hit', False)

                db_ops.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=result.get('response', 'Query executed successfully.'),
                    sql_query=result.get('sql'),
                    sql_params=[request.user_id],  # Parameters used in query
                    query_results_summary=results_summary,
                    execution_time=query_result.get('execution_time', 0),
                    model_version=result.get('model_used', 'unknown'),
                    metadata={
                        "cache_hit": cache_hit,
                        "column_count": len(query_result.get('columns', [])),
                    }
                )
                logger.info(f"💾 Stored assistant response")
            except Exception as e:
                logger.error(f"Failed to store assistant message: {e}")

        # =====================================================================
        # Step 7: Generate title for new conversation
        # =====================================================================
        if conversation_id and is_new_conversation:
            try:
                title = generate_conversation_title(request.query)
                db_ops.update_conversation_title(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    title=title
                )
                logger.info(f"📝 Generated title: '{title}'")
            except Exception as e:
                logger.error(f"Failed to generate title: {e}")

        # =====================================================================
        # Step 8: Return response
        # =====================================================================
        return ChatQueryResponse(
            success=True,
            user_query=request.query,
            generated_sql=result.get('sql'),
            results=results_list,
            columns=query_result.get('columns', []),
            row_count=query_result.get('row_count', 0),
            execution_time=query_result.get('execution_time', 0),
            natural_language_response=result.get('response', 'Query executed successfully.'),
            conversation_id=conversation_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat query: {str(e)}"
        )


def _generate_nl_response(query: str, results: List[dict], row_count: int) -> str:
    """
    Generate a natural language response from query results

    Args:
        query: Original user query
        results: Query results
        row_count: Number of rows returned

    Returns:
        Natural language response string
    """
    if row_count == 0:
        return "I couldn't find any results for your query."

    # Simple response generation based on query patterns
    query_lower = query.lower()

    # Handle COUNT queries
    if "how many" in query_lower or "count" in query_lower:
        if results and len(results) > 0:
            # Get the count value (should be the first value in the first row)
            count_value = list(results[0].values())[0]

            # Determine what we're counting
            if "transaction" in query_lower:
                return f"You have {count_value:,} transactions across your accounts."
            elif "account" in query_lower:
                return f"You have {count_value} accounts."
            else:
                return f"The count is {count_value:,}."

    # Handle SUM/TOTAL queries
    if "total" in query_lower or "sum" in query_lower:
        if results and len(results) > 0:
            total_value = list(results[0].values())[0]

            if "balance" in query_lower:
                return f"Your total balance is ${total_value:,.2f}."
            elif "spent" in query_lower or "spending" in query_lower:
                return f"You've spent ${abs(total_value):,.2f}."
            else:
                return f"The total is ${total_value:,.2f}."

    # Handle account listing
    if "account" in query_lower and ("show" in query_lower or "list" in query_lower):
        if row_count == 1:
            return f"You have 1 account."
        else:
            return f"You have {row_count} accounts."

    # Handle transaction listing
    if "transaction" in query_lower and ("show" in query_lower or "list" in query_lower or "recent" in query_lower):
        if row_count == 1:
            return f"Here is 1 transaction."
        else:
            return f"Here are {row_count} transactions."

    # Default responses
    if row_count == 1:
        return f"I found 1 result."
    else:
        return f"I found {row_count} results."


# ============================================================================
# Conversation API Endpoints
# ============================================================================

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreateRequest):
    """
    Create a new conversation

    Args:
        request: Conversation create request with user_id and optional title

    Returns:
        Created conversation data
    """
    try:
        # Create conversation
        conversation = db_ops.create_conversation(
            user_id=request.user_id,
            title=request.title
        )

        logger.info(f"✅ Created conversation {conversation['conversation_id']} for user {request.user_id}")

        return ConversationResponse(
            conversation_id=str(conversation["conversation_id"]),
            user_id=str(conversation["user_id"]),
            title=conversation.get("title"),
            created_at=str(conversation["created_at"]),
            updated_at=str(conversation["updated_at"]),
            last_message_at=str(conversation["last_message_at"]) if conversation.get("last_message_at") else None,
            is_archived=conversation.get("is_archived", False)
        )

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )


@app.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str,
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """
    List conversations for a user with pagination

    Args:
        user_id: User UUID
        include_archived: Include archived conversations
        limit: Maximum conversations to return
        offset: Pagination offset

    Returns:
        List of conversations
    """
    try:
        conversations = db_ops.get_user_conversations(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset
        )

        # Format conversations with message count
        formatted_conversations = []
        for conv in conversations:
            message_count = db_ops.get_conversation_message_count(
                conversation_id=str(conv["conversation_id"]),
                user_id=user_id
            )

            formatted_conversations.append(ConversationResponse(
                conversation_id=str(conv["conversation_id"]),
                user_id=str(conv["user_id"]),
                title=conv.get("title"),
                created_at=str(conv["created_at"]),
                updated_at=str(conv["updated_at"]),
                last_message_at=str(conv["last_message_at"]) if conv.get("last_message_at") else None,
                is_archived=conv.get("is_archived", False),
                message_count=message_count
            ))

        return ConversationListResponse(
            total=len(formatted_conversations),
            conversations=formatted_conversations
        )

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, user_id: str):
    """
    Get a specific conversation by ID

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)

    Returns:
        Conversation data
    """
    try:
        conversation = db_ops.get_conversation_by_id(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized"
            )

        message_count = db_ops.get_conversation_message_count(
            conversation_id=conversation_id,
            user_id=user_id
        )

        return ConversationResponse(
            conversation_id=str(conversation["conversation_id"]),
            user_id=str(conversation["user_id"]),
            title=conversation.get("title"),
            created_at=str(conversation["created_at"]),
            updated_at=str(conversation["updated_at"]),
            last_message_at=str(conversation["last_message_at"]) if conversation.get("last_message_at") else None,
            is_archived=conversation.get("is_archived", False),
            message_count=message_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation: {str(e)}"
        )


@app.get("/api/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    user_id: str,
    limit: int = 50,
    offset: int = 0
):
    """
    Get messages for a conversation with pagination

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)
        limit: Maximum messages to return
        offset: Pagination offset

    Returns:
        List of messages
    """
    try:
        messages = db_ops.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            order_desc=False  # Chronological order
        )

        formatted_messages = [
            MessageResponse(
                message_id=str(msg["message_id"]),
                conversation_id=str(msg["conversation_id"]),
                role=msg["role"],
                content=msg["content"],
                sql_query=msg.get("sql_query"),
                query_results_summary=msg.get("query_results_summary"),
                execution_time=float(msg["execution_time"]) if msg.get("execution_time") else None,
                error=msg.get("error"),
                model_version=msg.get("model_version"),
                metadata=msg.get("metadata", {}),
                created_at=str(msg["created_at"])
            )
            for msg in messages
        ]

        total_count = db_ops.get_conversation_message_count(
            conversation_id=conversation_id,
            user_id=user_id
        )

        return ConversationMessagesResponse(
            conversation_id=conversation_id,
            total_messages=total_count,
            messages=formatted_messages
        )

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}"
        )


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    user_id: str,
    request: ConversationUpdateRequest
):
    """
    Update conversation title

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)
        request: Update request with new title

    Returns:
        Success message
    """
    try:
        success = db_ops.update_conversation_title(
            conversation_id=conversation_id,
            user_id=user_id,
            title=request.title
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized"
            )

        return {"success": True, "message": "Conversation title updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )


@app.post("/api/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user_id: str):
    """
    Archive a conversation

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)

    Returns:
        Success message
    """
    try:
        success = db_ops.archive_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            archived=True
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized"
            )

        return {"success": True, "message": "Conversation archived"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive conversation: {str(e)}"
        )


@app.post("/api/conversations/{conversation_id}/unarchive")
async def unarchive_conversation(conversation_id: str, user_id: str):
    """
    Unarchive a conversation

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)

    Returns:
        Success message
    """
    try:
        success = db_ops.archive_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            archived=False
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized"
            )

        return {"success": True, "message": "Conversation unarchived"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unarchiving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unarchive conversation: {str(e)}"
        )


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str):
    """
    Soft delete a conversation

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID (for ownership verification)

    Returns:
        Success message
    """
    try:
        success = db_ops.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized"
            )

        return {"success": True, "message": "Conversation deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    chatbot_status = "enabled" if text2sql_pipeline else "disabled"
    return {
        "status": "healthy",
        "service": "nidhi-fi-backend",
        "text2sql_chatbot": chatbot_status
    }


@app.get("/api/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics

    Returns comprehensive caching metrics including:
    - Hit/miss rates
    - Total cached items
    - Cache backend information
    - Performance metrics

    Returns:
        Cache statistics dictionary
    """
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_detailed_stats()

        # Add helpful metrics
        if stats.get("enabled", False):
            total_requests = stats.get("total_requests", 0)
            if total_requests > 0:
                stats["cache_effectiveness"] = f"{stats.get('hit_rate', 0) * 100:.1f}%"
                stats["estimated_time_saved"] = f"{stats.get('hits', 0) * 10:.1f}s"  # Assuming ~10s per LLM call

        return stats

    except Exception as e:
        logger.error(f"Error fetching cache stats: {e}")
        return {"error": "Failed to fetch cache stats", "detail": str(e)}


@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear all cache entries

    WARNING: This will invalidate all cached responses
    Use with caution in production

    Returns:
        Success status
    """
    try:
        cache_manager = get_cache_manager()
        cache_manager.clear()
        logger.info("🗑️  Cache cleared via API")

        return {
            "success": True,
            "message": "Cache cleared successfully"
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


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
