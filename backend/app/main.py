"""
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings, create_directories
from app.db import init_db
from app.redis_client import redis_client
from app.ai.qdrant_client import qdrant_manager
from app.error_handlers import setup_error_handlers
from app.middleware import RequestTrackingMiddleware, MetricsMiddleware
from app.logging_config import setup_logging

# Configure logging with JSON formatting and sensitive data filtering
setup_logging(
    log_level=settings.LOG_LEVEL,
    use_json=(settings.ENVIRONMENT == "production"),
    filter_sensitive=True
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting FreeWill Video Platform...")
    
    # Create necessary directories
    create_directories()
    logger.info("Created storage directories")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Connect to Redis
    await redis_client.connect()
    
    # Connect to Qdrant
    qdrant_manager.connect()
    
    logger.info(f"Application started on {settings.INSTANCE_URL}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await redis_client.disconnect()
    qdrant_manager.disconnect()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A federated short-form video sharing platform with ActivityPub support",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(MetricsMiddleware, metrics_enabled=settings.ENABLE_METRICS)

# Setup error handlers
setup_error_handlers(app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "qdrant": "connected"
    }


# Import and include routers
from app.routers import posts, federation, interactions, users, moderation, feed, monitoring
app.include_router(posts.router)
app.include_router(federation.router)
app.include_router(interactions.router)
app.include_router(users.router)
app.include_router(moderation.router)
app.include_router(feed.router)
app.include_router(monitoring.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
