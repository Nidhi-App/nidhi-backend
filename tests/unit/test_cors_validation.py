"""Tests for CORS configuration validation."""

import pytest
import os
from unittest.mock import patch
from app.config import Settings


# Mock to prevent .env file from being loaded during tests
@pytest.fixture(autouse=True)
def mock_dotenv():
    """Prevent .env file from being loaded in tests."""
    with patch('pydantic_settings.sources.DotEnvSettingsSource.__call__', return_value={}):
        yield


class TestCORSValidation:
    """Test suite for CORS configuration validation."""

    def test_cors_allowed_empty_in_development(self):
        """Test that CORS_ORIGINS can be empty in development."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development',
            # CORS_ORIGINS not set - should be allowed in development
        }, clear=True):
            settings = Settings()

            # Should succeed without error
            assert settings.ENVIRONMENT == "development"
            assert settings.CORS_ORIGINS == []

    def test_cors_required_in_production(self):
        """Test that CORS_ORIGINS is required in production."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'LOGGING_SECRET': 'b' * 32,
            # CORS_ORIGINS not set - should fail
        }, clear=True):
            with pytest.raises(
                ValueError,
                match="CORS_ORIGINS must be explicitly set in production environment"
            ):
                Settings()

    def test_cors_explicit_config_accepted_in_production(self):
        """Test that explicit CORS_ORIGINS is accepted in production."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'CORS_ORIGINS': '["https://app.example.com", "https://www.example.com"]',
            'LOGGING_SECRET': 'b' * 32,
        }, clear=True):
            settings = Settings()

            # Should succeed with proper configuration
            assert settings.ENVIRONMENT == "production"
            assert len(settings.CORS_ORIGINS) == 2
            assert "https://app.example.com" in settings.CORS_ORIGINS
            assert "https://www.example.com" in settings.CORS_ORIGINS

    def test_cors_empty_list_rejected_in_production(self):
        """Test that empty CORS_ORIGINS list is rejected in production."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'CORS_ORIGINS': '[]',  # Explicitly empty list
            'LOGGING_SECRET': 'b' * 32,
        }, clear=True):
            with pytest.raises(
                ValueError,
                match="CORS_ORIGINS must be explicitly set in production environment"
            ):
                Settings()

    def test_cors_single_origin_accepted(self):
        """Test that a single CORS origin is accepted."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'CORS_ORIGINS': '["https://app.example.com"]',
            'LOGGING_SECRET': 'b' * 32,
        }, clear=True):
            settings = Settings()

            assert settings.CORS_ORIGINS == ["https://app.example.com"]

    def test_cors_with_wildcard_accepted_in_development(self):
        """Test that wildcard CORS is accepted in development (though not recommended)."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development',
            'CORS_ORIGINS': '["*"]',
        }, clear=True):
            settings = Settings()

            # Wildcard is allowed (though main.py will use it)
            assert settings.CORS_ORIGINS == ["*"]

    def test_cors_validation_message_is_helpful(self):
        """Test that validation error message provides helpful guidance."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'LOGGING_SECRET': 'b' * 32,
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()

            error_message = str(exc_info.value)
            # Verify error message is helpful
            assert "CORS_ORIGINS must be explicitly set" in error_message
            assert "block all cross-origin requests" in error_message
            assert "CORS_ORIGINS=https://app.example.com" in error_message

    def test_cors_allowed_empty_in_staging(self):
        """Test CORS behavior in staging environment (not production)."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'staging',
            # CORS_ORIGINS not set
        }, clear=True):
            settings = Settings()

            # Staging doesn't have the same strict requirement as production
            # But main.py will fail-fast if CORS_ORIGINS is empty
            assert settings.ENVIRONMENT == "staging"
            assert settings.CORS_ORIGINS == []
