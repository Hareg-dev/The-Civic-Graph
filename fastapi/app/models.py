"""
SQLAlchemy database models for the video platform
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy import TypeDecorator
from datetime import datetime
from app.db import Base
import json


class StringArray(TypeDecorator):
    """Custom type for storing arrays as JSON strings in SQLite"""
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100))
    bio = Column(Text)
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video_posts = relationship("VideoPost", back_populates="user", foreign_keys="VideoPost.user_id")
    interactions = relationship("UserInteraction", back_populates="user")
    did_document = relationship("DIDDocument", back_populates="user", uselist=False)


class VideoPost(Base):
    """Video post model with metadata and processing status"""
    __tablename__ = "video_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Content
    title = Column(String(200), nullable=False)
    description = Column(String(2000))
    tags = Column(StringArray, default=[])
    duration = Column(Integer)  # Duration in seconds
    
    # Processing status
    status = Column(String(20), default="processing", index=True)  # processing, ready, failed, rejected
    error_message = Column(Text)
    
    # File paths
    original_file_path = Column(String(500))
    thumbnail_small = Column(String(500))
    thumbnail_medium = Column(String(500))
    thumbnail_large = Column(String(500))
    resolutions = Column(JSON, default={})  # {360p: path, 480p: path, 720p: path, 1080p: path}
    
    # Federation
    is_federated = Column(Boolean, default=False, index=True)
    origin_instance = Column(String(255))
    origin_actor_did = Column(String(255))
    activitypub_id = Column(String(500), unique=True, index=True)
    
    # Engagement metrics
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0, index=True)
    
    # Moderation
    moderation_status = Column(String(20), default="pending", index=True)  # pending, approved, flagged, rejected
    moderation_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="video_posts", foreign_keys=[user_id])
    interactions = relationship("UserInteraction", back_populates="video_post")
    moderation_records = relationship("ModerationRecord", back_populates="video_post")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_video_posts_user_created', 'user_id', 'created_at'),
        Index('idx_video_posts_status_created', 'status', 'created_at'),
        Index('idx_video_posts_engagement', 'engagement_score', 'created_at'),
    )


class Activity(Base):
    """ActivityPub activity model for federation"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String(500), unique=True, nullable=False, index=True)  # ActivityPub ID (URL)
    activity_type = Column(String(50), nullable=False, index=True)  # Create, Like, Announce, Delete, Move
    actor = Column(String(500), nullable=False, index=True)  # Actor DID or URL
    object_id = Column(String(500), nullable=False, index=True)  # Target object ID
    object_type = Column(String(50))  # Video, Note, etc.
    content = Column(JSON, nullable=False)  # Full ActivityPub JSON
    is_local = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    delivery_records = relationship("DeliveryRecord", back_populates="activity")
    
    __table_args__ = (
        Index('idx_activities_type_created', 'activity_type', 'created_at'),
        Index('idx_activities_actor_created', 'actor', 'created_at'),
    )


class DeliveryRecord(Base):
    """Tracks delivery status of federated activities"""
    __tablename__ = "delivery_records"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False, index=True)
    inbox_url = Column(String(500), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, delivered, failed
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    next_retry_at = Column(DateTime, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    activity = relationship("Activity", back_populates="delivery_records")
    
    __table_args__ = (
        Index('idx_delivery_status_retry', 'status', 'next_retry_at'),
    )


class UserInteraction(Base):
    """Tracks user interactions with videos for recommendations"""
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    video_post_id = Column(Integer, ForeignKey("video_posts.id"), nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False, index=True)  # view, like, share, comment
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    video_post = relationship("VideoPost", back_populates="interactions")
    
    __table_args__ = (
        Index('idx_interactions_user_created', 'user_id', 'created_at'),
        Index('idx_interactions_user_type', 'user_id', 'interaction_type', 'created_at'),
    )


class ModerationRecord(Base):
    """Content moderation records"""
    __tablename__ = "moderation_records"
    
    id = Column(Integer, primary_key=True, index=True)
    video_post_id = Column(Integer, ForeignKey("video_posts.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, approved, flagged, rejected
    reason = Column(Text)
    severity = Column(String(20))  # low, medium, high
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    api_response = Column(JSON)  # Raw response from moderation API
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video_post = relationship("VideoPost", back_populates="moderation_records")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class DIDDocument(Base):
    """Decentralized Identifier document for portable identity"""
    __tablename__ = "did_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    did = Column(String(500), unique=True, nullable=False, index=True)  # did:key:...
    public_key = Column(Text, nullable=False)
    encrypted_private_key = Column(Text, nullable=False)
    current_instance_url = Column(String(500), nullable=False)
    previous_instance_url = Column(String(500))
    migration_status = Column(String(20))  # initiated, completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="did_document")


class Comment(Base):
    """Comments on video posts"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    video_post_id = Column(Integer, ForeignKey("video_posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("comments.id"))  # For nested comments
    is_federated = Column(Boolean, default=False)
    activitypub_id = Column(String(500), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video_post = relationship("VideoPost", foreign_keys=[video_post_id])
    user = relationship("User", foreign_keys=[user_id])
    parent = relationship("Comment", remote_side=[id], backref="replies")


class Follower(Base):
    """Follower relationships for federation"""
    __tablename__ = "followers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    follower_actor = Column(String(500), nullable=False, index=True)  # Actor URL or DID
    follower_inbox = Column(String(500), nullable=False)
    is_local = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    __table_args__ = (
        Index('idx_followers_user_actor', 'user_id', 'follower_actor', unique=True),
    )
