"""
Retry Utilities for Database and Service Operations
Implements exponential backoff and fallback strategies
Requirements: 10.5, 10.6, 10.7
"""

import logging
import asyncio
from typing import Callable, Any, Optional, TypeVar, List
from functools import wraps

from app.exceptions import DatabaseRetryExhaustedException

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_with_exponential_backoff(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    operation_name: str = "operation"
) -> Any:
    """
    Retry a function with exponential backoff
    Requirements: 10.5
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        exceptions: Tuple of exceptions to catch
        operation_name: Name of operation for logging
        
    Returns:
        Result of function call
        
    Raises:
        DatabaseRetryExhaustedException: If all retries exhausted
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()
            
            if attempt > 1:
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
            
            return result
            
        except exceptions as e:
            last_exception = e
            
            if attempt == max_attempts:
                logger.error(
                    f"{operation_name} failed after {max_attempts} attempts",
                    extra={
                        "operation": operation_name,
                        "attempts": max_attempts,
                        "last_error": str(e)
                    },
                    exc_info=True
                )
                raise DatabaseRetryExhaustedException(operation_name, max_attempts)
            
            logger.warning(
                f"{operation_name} failed on attempt {attempt}/{max_attempts}, retrying in {delay}s",
                extra={
                    "operation": operation_name,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "delay": delay,
                    "error": str(e)
                }
            )
            
            await asyncio.sleep(delay)
            delay = min(delay * exponential_base, max_delay)
    
    # Should never reach here, but just in case
    raise last_exception


def with_database_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0
):
    """
    Decorator for database operations with retry logic
    Requirements: 10.5
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_exponential_backoff(
                func=lambda: func(*args, **kwargs),
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                exceptions=(Exception,),  # Catch database-related exceptions
                operation_name=f"database_{func.__name__}"
            )
        return wrapper
    return decorator


class FallbackStrategy:
    """
    Fallback strategies for service failures
    Requirements: 10.6, 10.7
    """
    
    @staticmethod
    async def redis_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        operation_name: str = "redis_operation"
    ) -> Any:
        """
        Execute Redis operation with database fallback
        Requirements: 10.6
        
        Args:
            primary_func: Primary Redis operation
            fallback_func: Fallback database operation
            operation_name: Name for logging
            
        Returns:
            Result from primary or fallback
        """
        try:
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func()
            else:
                return primary_func()
                
        except Exception as e:
            logger.warning(
                f"Redis operation failed, falling back to database",
                extra={
                    "operation": operation_name,
                    "error": str(e)
                }
            )
            
            try:
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func()
                else:
                    return fallback_func()
                    
            except Exception as fallback_error:
                logger.error(
                    f"Fallback operation also failed",
                    extra={
                        "operation": operation_name,
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error)
                    },
                    exc_info=True
                )
                raise
    
    @staticmethod
    async def qdrant_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        operation_name: str = "qdrant_operation"
    ) -> Any:
        """
        Execute Qdrant operation with recency-based fallback
        Requirements: 10.7
        
        Args:
            primary_func: Primary Qdrant operation
            fallback_func: Fallback recency-based operation
            operation_name: Name for logging
            
        Returns:
            Result from primary or fallback
        """
        try:
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func()
            else:
                return primary_func()
                
        except Exception as e:
            logger.warning(
                f"Qdrant operation failed, falling back to recency-based ranking",
                extra={
                    "operation": operation_name,
                    "error": str(e)
                }
            )
            
            try:
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func()
                else:
                    return fallback_func()
                    
            except Exception as fallback_error:
                logger.error(
                    f"Fallback operation also failed",
                    extra={
                        "operation": operation_name,
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error)
                    },
                    exc_info=True
                )
                raise


class CircuitBreaker:
    """
    Circuit breaker pattern for external services
    Prevents cascading failures
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        import time
        
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset or close circuit
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful call")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures",
                    extra={"failure_count": self.failure_count}
                )
            
            raise
