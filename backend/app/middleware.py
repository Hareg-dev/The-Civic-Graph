"""
Middleware for Request Tracking and Logging
Requirements: 10.1, 10.2
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track requests with unique IDs and log request/response
    Requirements: 10.1, 10.2
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and add tracking
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with request ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log incoming request
        start_time = time.time()
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                },
                exc_info=True
            )
            
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect metrics
    Requirements: 10.8
    """
    
    def __init__(self, app, metrics_enabled: bool = True):
        super().__init__(app)
        self.metrics_enabled = metrics_enabled
        self.request_count = 0
        self.error_count = 0
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and collect metrics
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        if not self.metrics_enabled:
            return await call_next(request)
        
        self.request_count += 1
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Track error responses
            if response.status_code >= 400:
                self.error_count += 1
            
            # Emit metrics (in a real implementation, this would send to a metrics service)
            duration = time.time() - start_time
            
            if duration > 1.0:  # Log slow requests
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "status_code": response.status_code
                    }
                )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            raise
