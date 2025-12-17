"""
Feed Router
Handles personalized feed generation
Requirements: 4.1-4.8
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.ai.recsys import RecommendationEngine
from app.schemas import FeedResponse, VideoPostResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/feed",
    tags=["feed"]
)


# Placeholder for getting current user
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    # For now, return a test user
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


@router.get("", response_model=FeedResponse)
async def get_personalized_feed(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> FeedResponse:
    """
    Get personalized video feed for the current user
    Requirements: 4.1-4.8
    
    Returns videos ranked by:
    - User preference similarity (60%)
    - Recency (25%)
    - Engagement score (15%)
    
    Falls back to trending videos for users with insufficient history.
    
    Args:
        limit: Number of videos to return (1-100, default 20)
        cursor: Pagination cursor for next page
        
    Returns:
        Paginated feed with videos and next cursor
    """
    try:
        # Create recommendation engine
        rec_engine = RecommendationEngine(db)
        
        # Generate feed
        feed_result = await rec_engine.generate_feed(
            user_id=current_user.id,
            limit=limit,
            cursor=cursor
        )
        
        # Convert to response format
        videos = [
            VideoPostResponse(
                id=video.id,
                user_id=video.user_id,
                title=video.title,
                description=video.description,
                tags=video.tags or [],
                duration=video.duration,
                status=video.status,
                thumbnail_small=video.thumbnail_small,
                thumbnail_medium=video.thumbnail_medium,
                thumbnail_large=video.thumbnail_large,
                resolutions=video.resolutions or {},
                is_federated=video.is_federated,
                origin_instance=video.origin_instance,
                activitypub_id=video.activitypub_id,
                view_count=video.view_count,
                like_count=video.like_count,
                comment_count=video.comment_count,
                share_count=video.share_count,
                engagement_score=video.engagement_score,
                moderation_status=video.moderation_status,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
            for video in feed_result["videos"]
        ]
        
        return FeedResponse(
            videos=videos,
            next_cursor=feed_result.get("next_cursor"),
            has_more=feed_result.get("has_more", False)
        )
        
    except Exception as e:
        logger.error(f"Error generating feed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate feed"
        )


@router.get("/trending", response_model=List[VideoPostResponse])
async def get_trending_videos(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[VideoPostResponse]:
    """
    Get trending videos based on engagement from the past 24 hours
    Requirements: 4.6
    
    Args:
        limit: Number of videos to return
        
    Returns:
        List of trending videos
    """
    try:
        # Create recommendation engine
        rec_engine = RecommendationEngine(db)
        
        # Get trending videos
        trending = await rec_engine.get_trending_videos(limit=limit)
        
        # Convert to response format
        return [
            VideoPostResponse(
                id=video.id,
                user_id=video.user_id,
                title=video.title,
                description=video.description,
                tags=video.tags or [],
                duration=video.duration,
                status=video.status,
                thumbnail_small=video.thumbnail_small,
                thumbnail_medium=video.thumbnail_medium,
                thumbnail_large=video.thumbnail_large,
                resolutions=video.resolutions or {},
                is_federated=video.is_federated,
                origin_instance=video.origin_instance,
                activitypub_id=video.activitypub_id,
                view_count=video.view_count,
                like_count=video.like_count,
                comment_count=video.comment_count,
                share_count=video.share_count,
                engagement_score=video.engagement_score,
                moderation_status=video.moderation_status,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
            for video in trending
        ]
        
    except Exception as e:
        logger.error(f"Error getting trending videos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trending videos"
        )
