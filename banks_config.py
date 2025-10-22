"""
Bank configurations for fake bank onboarding
Contains metadata for US and Indian banks
"""

# Bank definitions with metadata
BANKS = {
    # US Banks
    "chase": {
        "name": "Chase Bank",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_chase_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/chase_1.png",
        "routing_number_prefix": "322271627"
    },
    "bofa": {
        "name": "Bank of America",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_bofa_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/bankofamerica_1.png",
        "routing_number_prefix": "026009593"
    },
    "wells_fargo": {
        "name": "Wells Fargo",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_wells_fargo_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/wellsfargo_1.png",
        "routing_number_prefix": "121000248"
    },
    "citi": {
        "name": "Citibank",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_citi_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/citibank_1.png",
        "routing_number_prefix": "021000089"
    },
    "discover": {
        "name": "Discover",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_discover_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/discover_1.png",
        "routing_number_prefix": "011000015"
    },
    "capital_one": {
        "name": "Capital One",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_capital_one_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/capitalone_1.png",
        "routing_number_prefix": "051405515"
    },
    "us_bank": {
        "name": "US Bank",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_us_bank_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/usbank_1.png",
        "routing_number_prefix": "042000013"
    },
    "pnc": {
        "name": "PNC Bank",
        "country": "US",
        "currency": "USD",
        "institution_id": "ins_pnc_fake",
        "logo_url": "https://plaid-merchant-logos.plaid.com/pnc_1.png",
        "routing_number_prefix": "043000096"
    },

    # Indian Banks
    "icici": {
        "name": "ICICI Bank",
        "country": "IN",
        "currency": "INR",
        "institution_id": "ins_icici_fake",
        "logo_url": "https://www.icicibank.com/content/dam/icicibank/india/assets/images/header/logo.png",
        "ifsc_prefix": "ICIC0"
    },
    "sbi": {
        "name": "State Bank of India",
        "country": "IN",
        "currency": "INR",
        "institution_id": "ins_sbi_fake",
        "logo_url": "https://www.onlinesbi.sbi/sbijsV2/images/sbi_logo_tagline.png",
        "ifsc_prefix": "SBIN0"
    },
    "hdfc": {
        "name": "HDFC Bank",
        "country": "IN",
        "currency": "INR",
        "institution_id": "ins_hdfc_fake",
        "logo_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/f4a3e55b-e54e-4bb0-8614-f4b3e0adf7b4/Personal/Pay/Cards/Credit%20Card/Standard%20Cards/HDFC-Bank-Logo.png",
        "ifsc_prefix": "HDFC0"
    },
    "axis": {
        "name": "Axis Bank",
        "country": "IN",
        "currency": "INR",
        "institution_id": "ins_axis_fake",
        "logo_url": "https://www.axisbank.com/images/default-source/default-album/axis-bank-logo.png",
        "ifsc_prefix": "UTIB0"
    },
    "kotak": {
        "name": "Kotak Mahindra Bank",
        "country": "IN",
        "currency": "INR",
        "institution_id": "ins_kotak_fake",
        "logo_url": "https://www.kotak.com/content/dam/Kotak/kotak-logo.png",
        "ifsc_prefix": "KKBK0"
    },
}

# Account type configurations
ACCOUNT_TYPES = {
    "checking": {
        "type": "depository",
        "subtype": "checking",
        "balance_range_usd": (500, 15000),
        "balance_range_inr": (10000, 300000),
        "name_format": "{bank} Checking"
    },
    "savings": {
        "type": "depository",
        "subtype": "savings",
        "balance_range_usd": (2000, 75000),
        "balance_range_inr": (50000, 1500000),
        "name_format": "{bank} Savings"
    },
    "credit_card": {
        "type": "credit",
        "subtype": "credit card",
        "balance_range_usd": (0, 5000),
        "balance_range_inr": (0, 100000),
        "credit_limit_range_usd": (3000, 25000),
        "credit_limit_range_inr": (60000, 500000),
        "name_format": "{bank} Credit Card"
    },
    "money_market": {
        "type": "depository",
        "subtype": "money market",
        "balance_range_usd": (10000, 100000),
        "balance_range_inr": (200000, 2000000),
        "name_format": "{bank} Money Market"
    }
}

# Transaction categories (realistic categories for expense tracking)
TRANSACTION_CATEGORIES = [
    "Food and Drink",
    "Restaurants",
    "Fast Food",
    "Coffee Shops",
    "Groceries",
    "Shops",
    "Department Stores",
    "Online Shopping",
    "Clothing Stores",
    "Electronics",
    "Home Improvement",
    "Transportation",
    "Gas Stations",
    "Public Transportation",
    "Rideshare",
    "Parking",
    "Automotive",
    "Entertainment",
    "Movies and TV",
    "Music and Audio",
    "Games",
    "Sports and Recreation",
    "Healthcare",
    "Fitness and Wellness",
    "Personal Care",
    "Pet Services",
    "Financial",
    "Bank Transfer",
    "Credit Card Payment",
    "Investment",
    "Loan Payment",
    "ATM Withdrawal",
    "Travel",
    "Hotels and Lodging",
    "Airlines",
    "Rental Cars",
    "Education",
    "Books and Magazines",
    "Utilities",
    "Insurance",
    "Taxes",
    "Government Services",
    "Charitable Giving",
    "Legal Services",
    "Professional Services",
    "Rent",
    "Mortgage",
]

# Payment channels
PAYMENT_CHANNELS = ["online", "in_store", "atm", "other"]

# Account status enum
ACCOUNT_STATUSES = ["Active", "Pending", "Completed", "Expired", "Failed"]

# Connection status enum
CONNECTION_STATUSES = ["Active", "Needs_Reauth", "Error", "Revoked"]

# Transaction directions
TRANSACTION_DIRECTIONS = ["Credit", "Debit"]


def get_us_banks():
    """Get list of US banks"""
    return {k: v for k, v in BANKS.items() if v["country"] == "US"}


def get_indian_banks():
    """Get list of Indian banks"""
    return {k: v for k, v in BANKS.items() if v["country"] == "IN"}


def get_bank_by_code(bank_code: str):
    """Get bank configuration by code"""
    return BANKS.get(bank_code)


def get_all_banks():
    """Get all banks organized by region"""
    return {
        "us_banks": [
            {"code": code, **bank_data}
            for code, bank_data in BANKS.items()
            if bank_data["country"] == "US"
        ],
        "indian_banks": [
            {"code": code, **bank_data}
            for code, bank_data in BANKS.items()
            if bank_data["country"] == "IN"
        ],
    }
