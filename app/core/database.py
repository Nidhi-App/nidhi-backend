"""Database connection and helper functions."""
import threading
from typing import Optional

from supabase import Client, create_client

from app.config import settings
from app.utils.logger import logger


class Database:
    """Thread-safe Supabase database client wrapper with singleton pattern."""

    _client: Optional[Client] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client instance (thread-safe).

        Uses double-checked locking pattern to ensure thread safety
        while minimizing lock contention.

        Returns:
            Client: Supabase client instance

        Raises:
            ValueError: If Supabase configuration is invalid
            Exception: If client creation fails
        """
        # First check (no lock) - fast path for already initialized client
        if cls._client is not None:
            return cls._client

        # Acquire lock for initialization
        with cls._lock:
            # Second check (with lock) - ensure only one thread initializes
            if cls._client is None:
                try:
                    logger.info("Initializing Supabase client...")

                    # Validate configuration
                    if not settings.SUPABASE_URL:
                        raise ValueError(
                            "SUPABASE_URL is not configured. "
                            "Please set the SUPABASE_URL environment variable."
                        )
                    if not settings.SUPABASE_KEY:
                        raise ValueError(
                            "SUPABASE_KEY is not configured. "
                            "Please set the SUPABASE_KEY environment variable."
                        )

                    # Create client
                    cls._client = create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_KEY
                    )

                    logger.info("Supabase client initialized successfully")

                except ValueError as e:
                    logger.error(f"Invalid Supabase configuration: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Failed to create Supabase client: {e}")
                    # Ensure we don't leave _client in partially initialized state
                    cls._client = None
                    raise Exception(
                        f"Failed to initialize database client: {e}. "
                        "Please check your Supabase configuration."
                    ) from e

            return cls._client

    @classmethod
    def reset_client(cls):
        """Reset client with proper cleanup and thread safety.

        This method safely resets the client singleton, ensuring:
        - Thread-safe operation (synchronized with get_client)
        - Proper resource cleanup before resetting
        - Exception handling during cleanup
        - No partial state if cleanup fails

        Useful for testing or when forcing client reinitialization.
        """
        with cls._lock:
            if cls._client is not None:
                logger.info("Resetting Supabase client...")

                # Attempt to clean up client resources
                try:
                    has_close = False
                    has_aclose = False

                    # Check for sync cleanup method (close) and call it if present
                    if hasattr(cls._client, 'close') and callable(getattr(cls._client, 'close')):
                        has_close = True
                        logger.debug("Calling client close() method")
                        try:
                            cls._client.close()
                            logger.debug("Client closed successfully")
                        except Exception as close_error:
                            logger.warning(f"Error during client close: {close_error}")
                            # Continue with reset despite close error

                    # Check for async cleanup method (aclose) - log but cannot await in sync context
                    if hasattr(cls._client, 'aclose') and callable(getattr(cls._client, 'aclose')):
                        has_aclose = True
                        logger.debug("Client has aclose() method, but cannot await in sync context")
                        logger.warning(
                            "Client has async cleanup method. "
                            "Consider using async context for proper cleanup."
                        )

                    # Log if no cleanup methods are available
                    if not has_close and not has_aclose:
                        logger.debug(
                            "Supabase client has no explicit close() method. "
                            "Relying on garbage collection for cleanup."
                        )

                except Exception as e:
                    # Catch any unexpected errors during cleanup attempt
                    logger.error(f"Unexpected error during client cleanup: {e}")
                    # Continue with reset despite cleanup error

                # Clear the reference to allow garbage collection
                cls._client = None
                logger.info("Supabase client reset complete")
            else:
                logger.debug("reset_client() called but client is already None")


# Convenience function for getting database client
def get_db() -> Client:
    """Get database client instance."""
    return Database.get_client()
