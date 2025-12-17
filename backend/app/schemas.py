"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class VideoStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    REJECTED = "rejected"


class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class InteractionType(str, Enum):
    VIEW = "view"
    LIKE = "like"
    SHARE = "share"
    COMMENT = "comment"


class ActivityType(str, Enum):
    CREATE = "Create"
    LIKE = "Like"
    ANNOUNCE = "Announce"
    DELETE = "Delete"
    MOVE = "Move"


# User Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Video Post Schemas
class VideoMetadata(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default=[], max_items=10)
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return [tag[:50] for tag in v]  # Limit tag length


class VideoPostCreate(VideoMetadata):
    pass


class VideoPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None, max_items=10)


class VideoPostResponse(VideoMetadata):
    id: int
    user_id: int
    duration: Optional[int]
    status: VideoStatus
    thumbnail_small: Optional[str]
    thumbnail_medium: Optional[str]
    thumbnail_large: Optional[str]
    resolutions: Dict[str, str]
    is_federated: bool
    origin_instance: Optional[str]
    activitypub_id: Optional[str]
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    engagement_score: float
    moderation_status: ModerationStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Upload Session Schemas
class UploadSessionCreate(BaseModel):
    filename: str
    file_size: int
    total_chunks: int = 1


class UploadSessionResponse(BaseModel):
    session_id: str
    user_id: int
    filename: str
    file_size: int
    total_chunks: int
    uploaded_chunks: List[int]
    status: str
    created_at: datetime
    expires_at: datetime


class ChunkUpload(BaseModel):
    session_id: str
    chunk_number: int
    checksum: str


# Interaction Schemas
class InteractionCreate(BaseModel):
    video_post_id: int
    interaction_type: InteractionType


class InteractionResponse(BaseModel):
    id: int
    user_id: int
    video_post_id: int
    interaction_type: InteractionType
    created_at: datetime
    
    class Config:
        from_attributes = True


# Feed Schemas
class FeedRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: Optional[str] = None


class FeedResponse(BaseModel):
    videos: List[VideoPostResponse]
    next_cursor: Optional[str]
    has_more: bool


# ActivityPub Schemas
class ActivityPubObject(BaseModel):
    id: str
    type: str
    actor: str
    object: Dict[str, Any]
    published: Optional[datetime]


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    object_id: str
    object_type: str
    content: Dict[str, Any]


class ActivityResponse(BaseModel):
    id: int
    activity_id: str
    activity_type: ActivityType
    actor: str
    object_id: str
    is_local: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Moderation Schemas
class ModerationReview(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|delete)$")
    reason: Optional[str] = None


class ModerationRecordResponse(BaseModel):
    id: int
    video_post_id: int
    status: ModerationStatus
    reason: Optional[str]
    severity: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# DID Schemas
class DIDCreate(BaseModel):
    password: str = Field(..., min_length=8)


class DIDResponse(BaseModel):
    did: str
    public_key: str
    current_instance_url: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MigrationInitiate(BaseModel):
    new_instance_url: str
    password: str


# Comment Schemas
class CommentCreate(BaseModel):
    video_post_id: int
    content: str = Field(..., min_length=1, max_length=2000)
    parent_comment_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    video_post_id: int
    user_id: int
    content: str
    parent_comment_id: Optional[int]
    is_federated: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Error Response Schema
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: str
    details: Optional[Dict[str, Any]] = None


# Validation Result Schema
class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


# Processing Result Schemas
class TranscodeResult(BaseModel):
    success: bool
    resolutions: Dict[str, str]
    thumbnails: Dict[str, str]
    duration: int
    error: Optional[str] = None


class EmbeddingResult(BaseModel):
    success: bool
    embedding: Optional[List[float]] = None
    dimension: Optional[int] = None
    error: Optional[str] = None
