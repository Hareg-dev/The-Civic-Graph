"""
Logging Configuration with JSON Formatting and Sensitive Data Filtering
Requirements: 10.8
"""

import logging
import json
import sys
from typing import Any, Dict
from datetime import datetime


class SensitiveDataFilter(logging.Filter):
    """
    Filter to remove sensitive data from logs
    Requirements: 10.8
    """
    
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "api_key",
        "secret",
        "private_key",
        "encrypted_private_key",
        "authorization",
        "cookie",
        "session"
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter sensitive data from log record
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always allow record, just filter data)
        """
        # Filter message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for field in self.SENSITIVE_FIELDS:
                if field in record.msg.lower():
                    record.msg = record.msg.replace(field, "[REDACTED]")
        
        # Filter extra fields
        if hasattr(record, '__dict__'):
            for key in list(record.__dict__.keys()):
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    record.__dict__[key] = "[REDACTED]"
        
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    Requirements: 10.8
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                              'levelname', 'levelno', 'lineno', 'module', 'msecs',
                              'message', 'pathname', 'process', 'processName',
                              'relativeCreated', 'thread', 'threadName', 'exc_info',
                              'exc_text', 'stack_info']:
                    log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    use_json: bool = False,
    filter_sensitive: bool = True
) -> None:
    """
    Setup logging configuration
    Requirements: 10.8
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        filter_sensitive: Whether to filter sensitive data
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    if filter_sensitive:
        console_handler.addFilter(SensitiveDataFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class MetricsCollector:
    """
    Metrics collector for monitoring
    Requirements: 10.8
    """
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "upload_count": 0,
            "upload_success": 0,
            "upload_failure": 0,
            "processing_count": 0,
            "processing_success": 0,
            "processing_failure": 0,
            "delivery_count": 0,
            "delivery_success": 0,
            "delivery_failure": 0,
            "api_requests": 0,
            "api_errors": 0
        }
    
    def increment(self, metric: str, value: int = 1) -> None:
        """
        Increment a metric
        
        Args:
            metric: Metric name
            value: Value to increment by
        """
        if metric in self.metrics:
            self.metrics[metric] += value
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.copy()
    
    def reset(self) -> None:
        """Reset all metrics to zero"""
        for key in self.metrics:
            self.metrics[key] = 0


# Global metrics collector instance
metrics_collector = MetricsCollector()
