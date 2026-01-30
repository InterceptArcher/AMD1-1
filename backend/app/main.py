"""
FastAPI app initialization and middleware setup.
"""

import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import enrichment

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager for app startup/shutdown.
    Used to initialize and cleanup resources.
    """
    logger.info("FastAPI app starting up")
    try:
        # Validate settings
        settings.validate()
        logger.info("Configuration validated")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    yield
    
    logger.info("FastAPI app shutting down")


# Create FastAPI app
app = FastAPI(
    title="AMD1-1 Alpha - Personalization Pipeline",
    description="RAD enrichment API for LinkedIn ebook personalization",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(enrichment.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AMD1-1 Alpha Personalization Pipeline",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/status")
async def status_check():
    """Application status check."""
    return {
        "status": "running",
        "debug": settings.DEBUG,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
