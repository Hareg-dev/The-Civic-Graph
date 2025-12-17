"""
Configuration management for the video platform
Loads settings from environment variables with sensible defaults
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "FreeWill Video Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    INSTANCE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/freewill"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "video_embeddings"
    QDRANT_VECTOR_SIZE: int = 512
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    PROCESSED_DIR: str = "processed"
    FEDERATED_DIR: str = "federated"
    MAX_UPLOAD_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_SEC: int = 180
    SUPPORTED_VIDEO_FORMATS: list = ["mp4", "webm", "mov"]
    
    # Video Processing
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    TRANSCODE_RESOLUTIONS: list = ["360p", "480p", "720p", "1080p"]
    THUMBNAIL_SIZES: dict = {
        "small": (160, 90),
        "medium": (320, 180),
        "large": (640, 360)
    }
    THUMBNAIL_TIMESTAMP_SEC: int = 2
    
    # AI/ML
    VISION_MODEL_NAME: str = "openai/clip-vit-base-patch32"
    TEXT_MODEL_NAME: str = "all-MiniLM-L6-v2"  # sentence-transformers model
    EMBEDDING_DIMENSION: int = 512
    EMBEDDING_RETRY_ATTEMPTS: int = 3
    EMBEDDING_RETRY_BACKOFF_SEC: int = 1
    USE_OLLAMA: bool = False  # Set to True to use Ollama for vision (e.g., SmolVLM)
    OLLAMA_MODEL: str = "smolvlm"  # Ollama model name if USE_OLLAMA is True
    OLLAMA_URL: str = "http://localhost:11434"  # Ollama API endpoint
    
    # Recommendation
    INTERACTION_LOOKBACK_DAYS: int = 30
    SIMILARITY_WEIGHT: float = 0.6
    RECENCY_WEIGHT: float = 0.25
    ENGAGEMENT_WEIGHT: float = 0.15
    FEED_PAGE_SIZE: int = 20
    TRENDING_WINDOW_HOURS: int = 24
    COLD_START_INTERACTION_THRESHOLD: int = 5
    
    # Federation
    FEDERATION_ENABLED: bool = True
    DELIVERY_RETRY_ATTEMPTS: int = 5
    DELIVERY_RETRY_DELAYS_MIN: list = [1, 5, 15, 60, 240]  # 1m, 5m, 15m, 1h, 4h
    FEDERATION_TIMEOUT_SEC: int = 30
    
    # Authentication
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Moderation
    MODERATION_ENABLED: bool = False
    MODERATION_API_KEY: Optional[str] = None
    MODERATION_API_ENDPOINT: Optional[str] = None
    
    # Worker
    WORKER_CONCURRENCY: int = 4
    TASK_QUEUE_NAME: str = "video_tasks"
    
    # Monitoring
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True
    ENABLE_TRACING: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def create_directories():
    """Create necessary directories for file storage"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
    os.makedirs(settings.FEDERATED_DIR, exist_ok=True)
    
    # Create subdirectories for processed files
    for resolution in settings.TRANSCODE_RESOLUTIONS:
        os.makedirs(os.path.join(settings.PROCESSED_DIR, resolution), exist_ok=True)
    
    os.makedirs(os.path.join(settings.PROCESSED_DIR, "thumbnails"), exist_ok=True)
