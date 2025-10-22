"""
Fake data generator for bank accounts and transactions
Uses Faker library to generate realistic financial data
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union
from uuid import UUID
from faker import Faker

from banks_config import (
    ACCOUNT_TYPES,
    TRANSACTION_CATEGORIES,
    TRANSACTION_DIRECTIONS,
    PAYMENT_CHANNELS,
    ACCOUNT_STATUSES,
    get_bank_by_code,
)


class FakeDataGenerator:
    """Generate fake financial data for accounts and transactions"""

    def __init__(self):
        # Initialize Faker with US and Indian locales
        self.faker = Faker(['en_US', 'en_IN'])
        Faker.seed(random.randint(0, 10000))

    def generate_accounts_for_bank(
        self, user_id: str, bank_code: str, num_accounts: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate fake accounts for a specific bank

        Args:
            user_id: UUID of the user
            bank_code: Bank identifier (e.g., 'chase', 'icici')
            num_accounts: Number of accounts to generate (default: 10)

        Returns:
            List of account data dictionaries
        """
        bank_config = get_bank_by_code(bank_code)
        if not bank_config:
            raise ValueError(f"Invalid bank code: {bank_code}")

        accounts = []
        currency = bank_config["currency"]
        is_usd = currency == "USD"

        # Distribution: 3 checking, 3 savings, 3 credit cards, 1 money market
        account_distribution = (
            ["checking"] * 3 + ["savings"] * 3 + ["credit_card"] * 3 + ["money_market"] * 1
        )

        # Shuffle for variety
        random.shuffle(account_distribution)

        for i, account_type_key in enumerate(account_distribution[:num_accounts]):
            account_type_config = ACCOUNT_TYPES[account_type_key]

            # Get balance range based on currency
            if is_usd:
                balance_range = account_type_config["balance_range_usd"]
                credit_limit_range = account_type_config.get("credit_limit_range_usd")
            else:
                balance_range = account_type_config["balance_range_inr"]
                credit_limit_range = account_type_config.get("credit_limit_range_inr")

            # Generate balance
            current_balance = round(random.uniform(*balance_range), 2)

            # Generate credit limit for credit cards
            credit_limit = None
            if account_type_key == "credit_card" and credit_limit_range:
                credit_limit = round(random.uniform(*credit_limit_range), 2)

            # Generate account number (last 4 digits)
            mask = str(self.faker.random_int(min=1000, max=9999))

            # Generate external account ID
            external_account_id = f"{bank_code}_{self.faker.random_int(min=100000, max=999999)}"

            # Generate account identifiers
            provider_metadata = {}
            if is_usd:
                provider_metadata = {
                    "routing_number": bank_config.get("routing_number_prefix", "000000000"),
                    "account_number": f"{self.faker.random_int(min=1000000000, max=9999999999)}",
                    "wire_routing": self.faker.random_int(min=100000000, max=999999999),
                }
            else:
                provider_metadata = {
                    "ifsc_code": f"{bank_config.get('ifsc_prefix', 'XXXX0')}{self.faker.random_int(min=100000, max=999999)}",
                    "account_number": f"{self.faker.random_int(min=10000000000, max=99999999999)}",
                }

            # Build account data
            account_data = {
                "user_id": user_id,
                "external_account_id": external_account_id,
                "name": account_type_config["name_format"].format(bank=bank_config["name"]),
                "account_type": account_type_config["type"],
                "account_subtype": account_type_config["subtype"],
                "currency": currency,
                "mask": mask,
                "provider_metadata": provider_metadata,
                "account_status": "Active",
                "current_balance": current_balance,
                "available_balance": current_balance if account_type_key != "credit_card" else (credit_limit - current_balance if credit_limit else 0),
                "credit_limit": credit_limit,
                "institution_name": bank_config["name"],
                "institution_country": bank_config["country"],
                "official_name": account_type_config["name_format"].format(bank=bank_config["name"]),
                "verification_status": "verified",
                "holder_category": "personal",
                "last_refreshed_at": datetime.utcnow().isoformat(),
            }

            accounts.append(account_data)

        return accounts

    def generate_transactions_for_account(
        self,
        account_id: Union[UUID, str],
        account_type: str,
        account_subtype: str,
        current_balance: float,
        currency: str,
        credit_limit: float = None,
        num_transactions: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Generate fake transactions for an account

        Args:
            account_id: Account ID
            account_type: Account type (depository/credit)
            account_subtype: Account subtype (checking/savings/credit card)
            current_balance: Current account balance
            currency: Currency code (USD/INR)
            credit_limit: Credit limit (for credit cards)
            num_transactions: Number of transactions to generate (default: 1000)

        Returns:
            List of transaction data dictionaries
        """
        transactions = []
        is_usd = currency == "USD"
        is_credit_account = account_type == "credit"

        # Randomize number of transactions (1000-1200 for variety)
        num_transactions = random.randint(num_transactions, num_transactions + 200)

        # Start with a calculated opening balance
        # Work backwards from current balance
        running_balance = current_balance

        # Generate transactions in chronological order (oldest to newest)
        for i in range(num_transactions):
            # Calculate date - spread over last 365 days
            days_ago = 365 - int((i / num_transactions) * 365)
            txn_date = datetime.now() - timedelta(days=days_ago)
            posted_at = txn_date + timedelta(hours=random.randint(1, 24))

            # Determine transaction direction (60% debit, 40% credit for variety)
            direction = random.choices(
                TRANSACTION_DIRECTIONS, weights=[40, 60], k=1
            )[0]

            # Generate realistic amounts based on currency and direction
            if is_usd:
                if direction == "Debit":
                    amount = round(random.uniform(5.00, 500.00), 2)
                else:  # Credit
                    amount = round(random.uniform(10.00, 2000.00), 2)
            else:  # INR
                if direction == "Debit":
                    amount = round(random.uniform(100.00, 10000.00), 2)
                else:  # Credit
                    amount = round(random.uniform(500.00, 50000.00), 2)

            # Calculate new running balance based on account type
            if is_credit_account:
                # For credit cards: Debit increases balance (debt), Credit decreases
                if direction == "Debit":
                    new_balance = running_balance + amount
                    # Check credit limit
                    if credit_limit and new_balance > credit_limit:
                        continue  # Skip this transaction
                else:  # Credit
                    new_balance = max(0, running_balance - amount)
            else:
                # For depository: Debit decreases balance, Credit increases
                if direction == "Debit":
                    new_balance = running_balance - amount
                    # Don't allow negative balance (skip transaction)
                    if new_balance < 0:
                        continue
                else:  # Credit
                    new_balance = running_balance + amount

            # Generate merchant and description
            merchant_name = self.faker.company()
            description = f"{merchant_name} - {self.faker.sentence(nb_words=3)}"

            # Select category
            category = random.choice(TRANSACTION_CATEGORIES)

            # Generate location
            location = {
                "city": self.faker.city(),
                "state": self.faker.state() if is_usd else self.faker.state(),
                "country": "US" if is_usd else "IN",
                "postal_code": self.faker.postcode(),
            }

            # Payment channel
            payment_channel = random.choice(PAYMENT_CHANNELS)

            # Personal finance category (Plaid-style)
            personal_finance_category = {
                "primary": category.split()[0].upper(),
                "detailed": category.upper().replace(" ", "_"),
            }

            # Pending status (10% pending)
            pending = random.random() < 0.1

            # Build transaction data
            transaction_data = {
                "account_id": account_id,
                "external_txn_id": f"txn_{self.faker.random_int(min=100000000, max=999999999)}",
                "txn_date": txn_date.date().isoformat(),
                "posted_at": posted_at.isoformat(),
                "authorized_date": txn_date.date().isoformat(),
                "amount": amount,
                "currency": currency,
                "txn_direction": direction,
                "description_raw": description,
                "merchant_name_raw": merchant_name,
                "merchant_logo_url": None,
                "merchant_website": f"https://www.{merchant_name.lower().replace(' ', '')}.com",
                "pending": pending,
                "running_balance": new_balance,
                "category": category,
                "personal_finance_category": personal_finance_category,
                "location": location,
                "payment_channel": payment_channel,
                "counterparties": [
                    {
                        "name": merchant_name,
                        "type": "merchant",
                    }
                ],
                "check_number": None,
                "provider_metadata": {
                    "merchant_category_code": str(self.faker.random_int(min=1000, max=9999)),
                    "transaction_type": random.choice(["purchase", "payment", "transfer", "withdrawal"]),
                },
                "raw_payload": {
                    "original_description": description,
                    "metadata": {
                        "by_order_of": None,
                        "payee": merchant_name if direction == "Debit" else None,
                        "payer": merchant_name if direction == "Credit" else None,
                    },
                },
            }

            transactions.append(transaction_data)
            running_balance = new_balance

        # Reverse to get chronological order (oldest first)
        transactions.reverse()

        return transactions

    def generate_connection_data(
        self, user_id: str, provider_id: int, bank_code: str
    ) -> Dict[str, Any]:
        """
        Generate connection data for a bank

        Args:
            user_id: User UUID
            provider_id: Provider ID
            bank_code: Bank code

        Returns:
            Connection data dictionary
        """
        bank_config = get_bank_by_code(bank_code)
        if not bank_config:
            raise ValueError(f"Invalid bank code: {bank_code}")

        connection_data = {
            "provider_id": provider_id,
            "user_id": user_id,
            "access_token": self.faker.sha256(),
            "external_item_id": f"item_{self.faker.random_int(min=100000, max=999999)}",
            "connection_status": "Active",
            "institution_id": bank_config["institution_id"],
            "institution_name": bank_config["name"],
            "products": ["transactions", "auth", "identity"],
            "available_products": ["investments", "liabilities", "assets"],
            "linked_at": datetime.utcnow().isoformat(),
            "last_synced_at": datetime.utcnow().isoformat(),
        }

        return connection_data
