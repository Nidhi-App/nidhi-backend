"""Enum definitions for the application."""
from enum import Enum


class AccountType(str, Enum):
    """Account type enum matching Plaid account types.

    Reference: https://plaid.com/docs/api/accounts/#account-type-schema
    """
    DEPOSITORY = "depository"
    CREDIT = "credit"
    LOAN = "loan"
    INVESTMENT = "investment"
    BROKERAGE = "brokerage"  # Legacy type, used for /assets/ endpoints only
    OTHER = "other"


class AccountSubtype(str, Enum):
    """Account subtype enum matching all Plaid account subtypes.

    Reference: https://plaid.com/docs/api/accounts/#account-type-schema
    Note: Plaid subtypes are case-sensitive and use lowercase with spaces.
    """
    # ========== Depository Subtypes ==========
    CHECKING = "checking"
    SAVINGS = "savings"
    HSA = "hsa"  # Health Savings Account
    CD = "cd"  # Certificate of Deposit
    MONEY_MARKET = "money market"
    PAYPAL = "paypal"
    PREPAID = "prepaid"
    CASH_MANAGEMENT = "cash management"
    EBT = "ebt"  # Electronic Benefits Transfer
    GIC = "gic"  # Guaranteed Investment Certificate

    # ========== Credit Subtypes ==========
    CREDIT_CARD = "credit card"
    # PAYPAL is also used for credit accounts

    # ========== Loan Subtypes ==========
    AUTO = "auto"
    BUSINESS = "business"
    COMMERCIAL = "commercial"
    CONSTRUCTION = "construction"
    CONSUMER = "consumer"
    HOME_EQUITY = "home equity"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OVERDRAFT = "overdraft"
    LINE_OF_CREDIT = "line of credit"
    STUDENT = "student"

    # ========== Investment Subtypes ==========
    RETIREMENT_401A = "401a"
    RETIREMENT_401K = "401k"
    RETIREMENT_403B = "403B"
    RETIREMENT_457B = "457b"
    RETIREMENT_529 = "529"
    BROKERAGE = "brokerage"
    CASH_ISA = "cash isa"
    CRYPTO_EXCHANGE = "crypto exchange"
    EDUCATION_SAVINGS_ACCOUNT = "education savings account"
    FIXED_ANNUITY = "fixed annuity"
    # GIC also used for investment
    HEALTH_REIMBURSEMENT_ARRANGEMENT = "health reimbursement arrangement"
    # HSA also used for investment
    IRA = "ira"
    ISA = "isa"
    KEOGH = "keogh"
    LIF = "lif"  # Life Income Fund
    LIFE_INSURANCE = "life insurance"
    LIRA = "lira"  # Locked-in Retirement Account
    LRIF = "lrif"  # Locked-in Retirement Income Fund
    LRSP = "lrsp"  # Locked-in Retirement Savings Plan
    MUTUAL_FUND = "mutual fund"
    NON_CUSTODIAL_WALLET = "non-custodial wallet"
    NON_TAXABLE_BROKERAGE_ACCOUNT = "non-taxable brokerage account"
    OTHER_ANNUITY = "other annuity"
    OTHER_INSURANCE = "other insurance"
    PAYROLL = "payroll"
    PENSION = "pension"
    PRIF = "prif"  # Prescribed Retirement Income Fund
    PROFIT_SHARING_PLAN = "profit sharing plan"
    QSHR = "qshr"  # Qualified Spousal Home Retention
    RDSP = "rdsp"  # Registered Disability Savings Plan
    RESP = "resp"  # Registered Education Savings Plan
    RETIREMENT = "retirement"
    RLIF = "rlif"  # Restricted Life Income Fund
    ROTH = "roth"
    ROTH_401K = "roth 401k"
    RRIF = "rrif"  # Registered Retirement Income Fund
    RRSP = "rrsp"  # Registered Retirement Savings Plan
    SARSEP = "sarsep"  # Salary Reduction Simplified Employee Pension
    SEP_IRA = "sep ira"
    SIMPLE_IRA = "simple ira"
    SIPP = "sipp"  # Self-Invested Personal Pension
    STOCK_PLAN = "stock plan"
    TFSA = "tfsa"  # Tax-Free Savings Account
    THRIFT_SAVINGS_PLAN = "thrift savings plan"
    TRUST = "trust"
    UGMA = "ugma"  # Uniform Gifts to Minors Act
    UTMA = "utma"  # Uniform Transfers to Minors Act
    VARIABLE_ANNUITY = "variable annuity"

    # ========== Other ==========
    OTHER = "other"


class TransactionDirection(str, Enum):
    """Transaction direction - money in or out."""
    CREDIT = "Credit"  # Money in (positive)
    DEBIT = "Debit"    # Money out (negative)
    UNKNOWN = "Unknown"


class ConnectionStatus(str, Enum):
    """Connection status enum matching database enum."""
    INITIALIZING = "Initializing"
    PENDING = "Pending"
    ACTIVE = "Active"
    NEEDS_REAUTH = "Needs_Reauth"
    ERROR = "Error"
    REVOKED = "Revoked"


class AccountStatus(str, Enum):
    """Account status enum matching database enum."""
    PENDING = "Pending"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    EXPIRED = "Expired"
    FAILED = "Failed"


class HolderCategory(str, Enum):
    """Holder category enum for account ownership type."""
    PERSONAL = "personal"
    BUSINESS = "business"
    UNRECOGNIZED = "unrecognized"
