"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.utils.logger import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Application starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Plaid Environment: {settings.PLAID_ENV}")

    # TODO: Initialize scheduler in Phase 7
    # TODO: Initialize database connection pool

    yield

    # Shutdown
    logger.info("👋 Application shutting down...")
    # TODO: Cleanup resources (close DB connections, shutdown scheduler)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Nidhi AI - Plaid Financial Data Integration",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Nidhi Backend API - Plaid Integration",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "plaid_env": settings.PLAID_ENV,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "plaid_configured": bool(settings.PLAID_CLIENT_ID and settings.PLAID_SECRET),
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
    }


# TODO: Include API routers in later phases
# from app.api.v1 import connections, accounts, transactions, webhooks
# app.include_router(connections.router, prefix="/api/v1", tags=["connections"])
# app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
# app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
# app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
