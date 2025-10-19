"""
Application configuration using Pydantic Settings.
Environment variables are loaded from .env file.
"""

import os
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Nidhi Backend - Plaid Integration"
    APP_VERSION: str = "0.1.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode (automatically True in development, must be False in production)"
    )

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Plaid
    PLAID_CLIENT_ID: str
    PLAID_SECRET: str
    PLAID_ENV: str = "sandbox"  # sandbox, development, production
    PLAID_WEBHOOK_URL: Optional[str] = None
    PLAID_WEBHOOK_VERIFICATION_KEY: Optional[str] = None

    # Security
    SECRET_KEY: str = Field(
        description="Secret key for JWT signing - MUST be set via environment variable"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of allowed CORS origins"
    )

    # Sentry (Error Tracking)
    SENTRY_DSN: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOGGING_SECRET: Optional[str] = None  # Secret for hashing sensitive identifiers in logs

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is set and sufficiently strong.

        Args:
            v: Secret key value

        Returns:
            Validated secret key

        Raises:
            ValueError: If secret key is invalid or insecure
        """
        if not v:
            raise ValueError(
                "SECRET_KEY must be set in environment variables. "
                "Generate a secure random string of at least 32 characters."
            )
        if len(v) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters long, got {len(v)} characters. "
                "Use a cryptographically secure random string."
            )
        if v.startswith("your-secret-key") or v == "changeme" or v == "secret":
            raise ValueError(
                "SECRET_KEY must not use default/example value. "
                "Generate a unique secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

    @field_validator('PLAID_CLIENT_ID', 'PLAID_SECRET')
    @classmethod
    def validate_plaid_credentials(cls, v: str, info) -> str:
        """Validate Plaid credentials are set and not placeholder values.

        Args:
            v: Credential value
            info: Field info

        Returns:
            Validated credential

        Raises:
            ValueError: If credential is invalid
        """
        if not v:
            raise ValueError(f"{info.field_name} must be set in environment variables")
        if v.startswith("your-") or v == "changeme":
            raise ValueError(
                f"{info.field_name} contains placeholder value. "
                "Set real Plaid credentials from https://dashboard.plaid.com/"
            )
        return v

    @field_validator('PLAID_ENV')
    @classmethod
    def validate_plaid_env(cls, v: str) -> str:
        """Validate Plaid environment.

        Args:
            v: Plaid environment value

        Returns:
            Validated environment

        Raises:
            ValueError: If environment is invalid
        """
        allowed = ["sandbox", "development", "production"]
        if v not in allowed:
            raise ValueError(
                f"PLAID_ENV must be one of {allowed}, got '{v}'. "
                "See https://plaid.com/docs/api/tokens/#linktokencreate for details."
            )
        return v

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list.

        Args:
            v: CORS origins as string or list

        Returns:
            List of origin URLs
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v or []

    @model_validator(mode='after')
    def validate_environment_config(self):
        """Validate environment-specific configuration requirements.

        Returns:
            Validated settings instance

        Raises:
            ValueError: If production requirements are not met
        """
        # Auto-enable DEBUG in development if not explicitly set
        if self.ENVIRONMENT == "development":
            if 'DEBUG' not in os.environ:
                self.DEBUG = True

        # Validate production requirements
        if self.ENVIRONMENT == "production":
            # Require Supabase in production
            if not self.SUPABASE_URL or not self.SUPABASE_KEY:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_KEY must be set in production environment"
                )

            # Require explicit CORS configuration in production
            if not self.CORS_ORIGINS:
                raise ValueError(
                    "CORS_ORIGINS must be explicitly set in production. "
                    "Specify allowed frontend origins (comma-separated): "
                    "CORS_ORIGINS=https://app.example.com,https://www.example.com"
                )

            # Validate Plaid production webhook
            if self.PLAID_ENV == "production" and not self.PLAID_WEBHOOK_VERIFICATION_KEY:
                raise ValueError(
                    "PLAID_WEBHOOK_VERIFICATION_KEY must be set when using production Plaid environment"
                )

            # Require logging secret in production
            if not self.LOGGING_SECRET:
                raise ValueError(
                    "LOGGING_SECRET must be set in production for secure log identifier hashing. "
                    "Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

            # Disable debug in production
            if self.DEBUG:
                raise ValueError(
                    "DEBUG must be False in production for security. "
                    "Remove DEBUG from environment variables or set DEBUG=False"
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
