"""
Custom Exception Classes for Domain Errors
Requirements: 10.1
"""

from typing import Optional, Dict, Any


class VideoPlatformException(Exception):
    """Base exception for all video platform errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class UploadException(VideoPlatformException):
    """Exceptions related to video upload"""
    pass


class InvalidFormatException(UploadException):
    """Invalid video format"""
    
    def __init__(self, format: str, supported_formats: list):
        super().__init__(
            message=f"Invalid video format: {format}",
            error_code="INVALID_FORMAT",
            status_code=400,
            details={
                "provided_format": format,
                "supported_formats": supported_formats
            }
        )


class FileTooLargeException(UploadException):
    """File size exceeds limit"""
    
    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"File size {size} bytes exceeds maximum {max_size} bytes",
            error_code="FILE_TOO_LARGE",
            status_code=413,
            details={
                "file_size": size,
                "max_size": max_size
            }
        )


class DurationExceededException(UploadException):
    """Video duration exceeds limit"""
    
    def __init__(self, duration: int, max_duration: int):
        super().__init__(
            message=f"Video duration {duration}s exceeds maximum {max_duration}s",
            error_code="DURATION_EXCEEDED",
            status_code=400,
            details={
                "duration": duration,
                "max_duration": max_duration
            }
        )


class CorruptedFileException(UploadException):
    """Video file is corrupted"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Video file is corrupted: {reason}",
            error_code="CORRUPTED_FILE",
            status_code=400,
            details={"reason": reason}
        )


class SessionExpiredException(UploadException):
    """Upload session has expired"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Upload session {session_id} has expired",
            error_code="SESSION_EXPIRED",
            status_code=410,
            details={"session_id": session_id}
        )


class InvalidChunkSequenceException(UploadException):
    """Invalid chunk sequence in upload"""
    
    def __init__(self, expected: int, received: int):
        super().__init__(
            message=f"Invalid chunk sequence: expected {expected}, received {received}",
            error_code="INVALID_CHUNK_SEQUENCE",
            status_code=400,
            details={
                "expected_chunk": expected,
                "received_chunk": received
            }
        )


class ChecksumMismatchException(UploadException):
    """Checksum verification failed"""
    
    def __init__(self, expected: str, actual: str):
        super().__init__(
            message="Checksum verification failed",
            error_code="CHECKSUM_MISMATCH",
            status_code=400,
            details={
                "expected_checksum": expected,
                "actual_checksum": actual
            }
        )


class ProcessingException(VideoPlatformException):
    """Exceptions related to video processing"""
    pass


class TranscodingFailedException(ProcessingException):
    """Video transcoding failed"""
    
    def __init__(self, video_id: int, reason: str):
        super().__init__(
            message=f"Transcoding failed for video {video_id}: {reason}",
            error_code="TRANSCODING_FAILED",
            status_code=500,
            details={
                "video_id": video_id,
                "reason": reason
            }
        )


class EmbeddingGenerationException(ProcessingException):
    """Embedding generation failed"""
    
    def __init__(self, video_id: int, reason: str):
        super().__init__(
            message=f"Embedding generation failed for video {video_id}: {reason}",
            error_code="EMBEDDING_FAILED",
            status_code=500,
            details={
                "video_id": video_id,
                "reason": reason
            }
        )


class FederationException(VideoPlatformException):
    """Exceptions related to federation"""
    pass


class InvalidSignatureException(FederationException):
    """Invalid HTTP signature"""
    
    def __init__(self, actor: str):
        super().__init__(
            message=f"Invalid signature from {actor}",
            error_code="INVALID_SIGNATURE",
            status_code=401,
            details={"actor": actor}
        )


class InvalidActivityException(FederationException):
    """Invalid ActivityPub activity"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid activity: {reason}",
            error_code="INVALID_ACTIVITY",
            status_code=400,
            details={"reason": reason}
        )


class DeliveryFailedException(FederationException):
    """Activity delivery failed"""
    
    def __init__(self, inbox_url: str, reason: str):
        super().__init__(
            message=f"Delivery to {inbox_url} failed: {reason}",
            error_code="DELIVERY_FAILED",
            status_code=500,
            details={
                "inbox_url": inbox_url,
                "reason": reason
            }
        )


class DatabaseException(VideoPlatformException):
    """Exceptions related to database operations"""
    pass


class DatabaseConnectionException(DatabaseException):
    """Database connection failed"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Database connection failed: {reason}",
            error_code="DATABASE_CONNECTION_FAILED",
            status_code=503,
            details={"reason": reason}
        )


class DatabaseRetryExhaustedException(DatabaseException):
    """Database retry attempts exhausted"""
    
    def __init__(self, operation: str, attempts: int):
        super().__init__(
            message=f"Database operation '{operation}' failed after {attempts} attempts",
            error_code="DATABASE_RETRY_EXHAUSTED",
            status_code=503,
            details={
                "operation": operation,
                "attempts": attempts
            }
        )


class ServiceException(VideoPlatformException):
    """Exceptions related to external services"""
    pass


class RedisConnectionException(ServiceException):
    """Redis connection failed"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Redis connection failed: {reason}",
            error_code="REDIS_CONNECTION_FAILED",
            status_code=503,
            details={"reason": reason}
        )


class QdrantConnectionException(ServiceException):
    """Qdrant connection failed"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Qdrant connection failed: {reason}",
            error_code="QDRANT_CONNECTION_FAILED",
            status_code=503,
            details={"reason": reason}
        )


class ModerationException(VideoPlatformException):
    """Exceptions related to content moderation"""
    pass


class ModerationAPIException(ModerationException):
    """Moderation API call failed"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Moderation API failed: {reason}",
            error_code="MODERATION_API_FAILED",
            status_code=503,
            details={"reason": reason}
        )
