# Nidhi-Fi Backend API

FastAPI backend for fake bank account onboarding with transaction generation.

## Features

- 🏦 Support for US and Indian banks
- 💳 Generate 10 fake accounts per bank
- 💰 Generate 1000+ realistic transactions per account
- 🔄 RESTful API with FastAPI
- 📊 Supabase integration for data storage

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or with virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Make sure `.env` file exists with Supabase credentials:

```env
SUPABASE_URL=https://lbojunyyqapvrjrhxsjk.supabase.co
SUPABASE_KEY=your-service-role-key-here
```

### 3. Run the Server

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --reload --port 5000
```

The API will be available at: `http://localhost:5000`

## API Endpoints

### 1. Get Available Banks

```http
GET /api/banks
```

**Response:**
```json
{
  "us_banks": [
    {
      "code": "chase",
      "name": "Chase Bank",
      "country": "US",
      "currency": "USD",
      "logo_url": "..."
    }
  ],
  "indian_banks": [
    {
      "code": "icici",
      "name": "ICICI Bank",
      "country": "IN",
      "currency": "INR",
      "logo_url": "..."
    }
  ]
}
```

### 2. Connect Bank (Generate Accounts)

```http
POST /api/banks/connect
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "bank_code": "chase"
}
```

**Response:**
```json
{
  "connection_id": 123,
  "institution_name": "Chase Bank",
  "accounts_created": 10,
  "accounts": [
    {
      "account_id": 1,
      "name": "Chase Checking",
      "mask": "4532",
      "account_type": "depository",
      "account_subtype": "checking",
      "current_balance": 5234.56,
      "currency": "USD"
    }
  ]
}
```

### 3. Select Accounts & Generate Transactions

```http
POST /api/accounts/select
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "account_ids": [1, 2, 3, 5, 7]
}
```

**Response:**
```json
{
  "success": true,
  "accounts_with_transactions": 5,
  "total_transactions_created": 5000,
  "message": "Successfully generated transactions"
}
```

### 4. Get Account Summary

```http
GET /api/accounts/summary?user_id={uuid}
```

**Response:**
```json
{
  "total_accounts": 5,
  "total_balance": 45234.56,
  "accounts": [
    {
      "account_id": 1,
      "name": "Chase Checking",
      "mask": "4532",
      "current_balance": 5234.56,
      "transaction_count": 1050,
      "institution_name": "Chase Bank"
    }
  ]
}
```

## Supported Banks

### US Banks
- Chase Bank
- Bank of America
- Wells Fargo
- Citibank
- Discover
- Capital One
- US Bank
- PNC Bank

### Indian Banks
- ICICI Bank
- State Bank of India (SBI)
- HDFC Bank
- Axis Bank
- Kotak Mahindra Bank

## Project Structure

```
nidhi-tmp-backend/
├── app.py                      # FastAPI application
├── banks_config.py             # Bank definitions and configurations
├── fake_data_generator.py      # Fake data generation logic
├── db_operations.py            # Supabase database operations
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── README.md                   # This file
```

## Development

### Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

### Testing

Test the API using curl:

```bash
# Get banks
curl http://localhost:5000/api/banks

# Connect bank
curl -X POST http://localhost:5000/api/banks/connect \
  -H "Content-Type: application/json" \
  -d '{"user_id": "your-uuid", "bank_code": "chase"}'

# Get account summary
curl "http://localhost:5000/api/accounts/summary?user_id=your-uuid"
```

## Notes

- Each bank generates exactly 10 accounts (3 checking, 3 savings, 3 credit cards, 1 money market)
- Each selected account generates 1000-1200 transactions
- Transactions are spread over the last 365 days
- Running balances are calculated correctly based on account type
- All data is realistic using the Faker library
