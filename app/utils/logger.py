"""
Logging configuration using Loguru.
Provides structured logging with rotation and retention.
"""

import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logger():
    """
    Configure Loguru logger with custom settings.

    Features:
    - Console output with color formatting
    - File output with daily rotation
    - 30-day log retention
    - JSON formatting for production
    """

    # Remove default handler
    logger.remove()

    # Console handler - colored output for development
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File handler - rotating daily, 30-day retention
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
    )

    # JSON log file for production (easier parsing)
    if settings.ENVIRONMENT == "production":
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.json",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            serialize=True,  # JSON format
        )

    logger.info(f"Logger initialized - Level: {settings.LOG_LEVEL}, Environment: {settings.ENVIRONMENT}")

    return logger


# Initialize logger when module is imported
app_logger = setup_logger()
