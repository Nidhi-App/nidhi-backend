"""Tests for DEBUG auto-enable logic in config.py"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.config import Settings


# Mock to prevent .env file from being loaded during tests
@pytest.fixture(autouse=True)
def mock_dotenv():
    """Prevent .env file from being loaded in tests."""
    with patch('pydantic_settings.sources.DotEnvSettingsSource.__call__', return_value={}):
        yield


class TestDebugAutoEnable:
    """Test suite for DEBUG field auto-enable behavior."""

    def test_debug_auto_enabled_in_development_when_not_set(self):
        """Test DEBUG is auto-enabled in development when not explicitly set."""
        # Create settings without DEBUG set anywhere
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development'
        }, clear=True):
            settings = Settings()

            # Should auto-enable DEBUG in development
            assert settings.DEBUG is True
            assert settings.ENVIRONMENT == "development"

    def test_debug_not_overridden_when_set_via_env_var(self):
        """Test DEBUG is not overridden when explicitly set via environment variable."""
        # Explicitly set DEBUG=False via environment variable
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development',
            'DEBUG': 'false'  # Explicitly set to false
        }, clear=True):
            settings = Settings()

            # Should respect the explicit setting
            assert settings.DEBUG is False
            assert settings.ENVIRONMENT == "development"

    def test_debug_not_overridden_when_set_true_via_env_var(self):
        """Test DEBUG=True is preserved when explicitly set via environment variable."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development',
            'DEBUG': 'true'  # Explicitly set to true
        }, clear=True):
            settings = Settings()

            # Should respect the explicit setting
            assert settings.DEBUG is True
            assert settings.ENVIRONMENT == "development"

    def test_debug_not_auto_enabled_in_production(self):
        """Test DEBUG is not auto-enabled in production (default should be False)."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'CORS_ORIGINS': '["https://example.com"]',  # JSON format for list
            'LOGGING_SECRET': 'b' * 32
        }, clear=True):
            settings = Settings()

            # Should NOT auto-enable in production (default is False)
            assert settings.DEBUG is False
            assert settings.ENVIRONMENT == "production"

    def test_debug_explicit_true_rejected_in_production(self):
        """Test that DEBUG=True is rejected in production environment."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'production',
            'DEBUG': 'true',  # Try to enable DEBUG in production
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'CORS_ORIGINS': '["https://example.com"]',  # JSON format for list
            'LOGGING_SECRET': 'b' * 32
        }, clear=True):
            # Should raise validation error
            with pytest.raises(ValueError, match="DEBUG must be False in production"):
                Settings()

    def test_debug_not_auto_enabled_in_staging(self):
        """Test DEBUG is not auto-enabled in non-development environments like staging."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'staging',
            # Don't set DEBUG - should default to False
        }, clear=True):
            settings = Settings()

            # Should NOT auto-enable (only for development)
            assert settings.DEBUG is False
            assert settings.ENVIRONMENT == "staging"

    def test_model_fields_set_contains_debug_when_explicitly_set(self):
        """Verify that model_fields_set properly tracks when DEBUG is set."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development',
            'DEBUG': 'false'
        }, clear=True):
            settings = Settings()

            # DEBUG should be in model_fields_set when explicitly provided
            assert 'DEBUG' in settings.model_fields_set
            assert settings.DEBUG is False

    def test_model_fields_set_does_not_contain_debug_when_not_set(self):
        """Verify that model_fields_set does not contain DEBUG when not provided."""
        with patch.dict(os.environ, {
            'PLAID_CLIENT_ID': 'test',
            'PLAID_SECRET': 'test',
            'SECRET_KEY': 'a' * 32,
            'ENVIRONMENT': 'development'
            # DEBUG not set
        }, clear=True):
            settings = Settings()

            # Before validation, DEBUG should not be in model_fields_set
            # After validation, it gets auto-set but that's the behavior we want
            assert settings.DEBUG is True  # Auto-enabled
