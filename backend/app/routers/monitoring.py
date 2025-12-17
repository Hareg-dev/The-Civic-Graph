"""
Monitoring Router
Provides health checks and metrics endpoints
Requirements: 10.8
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.redis_client import redis_client
from app.ai.qdrant_client import qdrant_manager
from app.logging_config import metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/monitoring",
    tags=["monitoring"]
)


@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    Requirements: 10.8
    
    Checks status of all critical services:
    - Database
    - Redis
    - Qdrant
    
    Returns:
        Health status of all services
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis
    try:
        await redis_client.ping()
        health_status["services"]["redis"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(f"Redis health check failed: {e}")
    
    # Check Qdrant
    try:
        qdrant_manager.client.get_collections()
        health_status["services"]["qdrant"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["qdrant"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(f"Qdrant health check failed: {e}")
    
    return health_status


@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes
    
    Returns:
        Simple status indicating the app is running
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness probe for Kubernetes
    
    Checks if the app is ready to serve traffic
    
    Returns:
        Ready status
    """
    try:
        # Check database connection
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "reason": str(e)}


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics
    Requirements: 10.8
    
    Returns metrics for:
    - Upload rates
    - Processing times
    - Delivery success rates
    - API request counts
    
    Returns:
        Dictionary of metrics
    """
    metrics = metrics_collector.get_metrics()
    
    # Calculate rates and percentages
    if metrics["upload_count"] > 0:
        metrics["upload_success_rate"] = (
            metrics["upload_success"] / metrics["upload_count"] * 100
        )
    else:
        metrics["upload_success_rate"] = 0
    
    if metrics["processing_count"] > 0:
        metrics["processing_success_rate"] = (
            metrics["processing_success"] / metrics["processing_count"] * 100
        )
    else:
        metrics["processing_success_rate"] = 0
    
    if metrics["delivery_count"] > 0:
        metrics["delivery_success_rate"] = (
            metrics["delivery_success"] / metrics["delivery_count"] * 100
        )
    else:
        metrics["delivery_success_rate"] = 0
    
    if metrics["api_requests"] > 0:
        metrics["api_error_rate"] = (
            metrics["api_errors"] / metrics["api_requests"] * 100
        )
    else:
        metrics["api_error_rate"] = 0
    
    return metrics


@router.post("/metrics/reset")
async def reset_metrics() -> Dict[str, str]:
    """
    Reset all metrics to zero
    
    Returns:
        Success message
    """
    metrics_collector.reset()
    return {"status": "success", "message": "Metrics reset"}
