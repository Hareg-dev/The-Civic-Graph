"""
Error Handlers and Middleware
Implements structured error responses and logging
Requirements: 10.1, 10.2
"""

import logging
import uuid
import traceback
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import VideoPlatformException

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())


async def video_platform_exception_handler(
    request: Request,
    exc: VideoPlatformException
) -> JSONResponse:
    """
    Handle custom video platform exceptions
    Requirements: 10.1
    
    Args:
        request: FastAPI request
        exc: Custom exception
        
    Returns:
        Structured error response
    """
    request_id = getattr(request.state, "request_id", generate_request_id())
    
    # Log error with full context (Requirement 10.2)
    logger.error(
        f"VideoPlatformException: {exc.error_code}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    # Return structured error response (Requirement 10.1)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "request_id": request_id,
            "details": exc.details
        }
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions
    Requirements: 10.1
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        Structured error response
    """
    request_id = getattr(request.state, "request_id", generate_request_id())
    
    # Log error
    logger.warning(
        f"HTTPException: {exc.status_code}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Map status code to error code
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": exc.detail,
            "request_id": request_id,
            "details": {}
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors
    Requirements: 10.1
    
    Args:
        request: FastAPI request
        exc: Validation error
        
    Returns:
        Structured error response
    """
    request_id = getattr(request.state, "request_id", generate_request_id())
    
    # Log validation error
    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "request_id": request_id,
            "details": {
                "errors": exc.errors()
            }
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions
    Requirements: 10.1, 10.2
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        Structured error response
    """
    request_id = getattr(request.state, "request_id", generate_request_id())
    
    # Log error with full context (Requirement 10.2)
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Return generic error response (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "request_id": request_id,
            "details": {}
        }
    )


def setup_error_handlers(app):
    """
    Register error handlers with FastAPI app
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(VideoPlatformException, video_platform_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
