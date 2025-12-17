"""
Interactions Router
Handles user interactions with videos (likes, comments, shares)
Requirements: 7.1-7.8
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, VideoPost
from app.services.interaction_service import create_interaction_service
from app.schemas import CommentCreate, CommentResponse, InteractionResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/interactions",
    tags=["interactions"]
)


# Placeholder for getting current user
# In a real implementation, this would verify JWT tokens
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


@router.post("/videos/{video_id}/like", status_code=status.HTTP_200_OK)
async def like_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Like a video post
    Requirements: 7.1
    
    Creates a Like activity and delivers it to the origin instance if federated.
    
    Args:
        video_id: ID of the video to like
        
    Returns:
        Success message with activity info
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create interaction service
        interaction_service = create_interaction_service(db)
        
        # Create like
        result = await interaction_service.create_like(current_user, video_post)
        
        return {
            "status": "success",
            "message": "Video liked",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to like video"
        )


@router.delete("/videos/{video_id}/like", status_code=status.HTTP_200_OK)
async def unlike_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Unlike a video post
    
    Args:
        video_id: ID of the video to unlike
        
    Returns:
        Success message
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Find and delete interaction
        from app.models import UserInteraction
        interaction = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.video_post_id == video_id,
            UserInteraction.interaction_type == "like"
        ).first()
        
        if not interaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Like not found"
            )
        
        db.delete(interaction)
        
        # Update counts
        video_post.like_count = max(0, video_post.like_count - 1)
        video_post.engagement_score = (
            video_post.like_count * 2 +
            video_post.comment_count * 3 +
            video_post.share_count * 4 +
            video_post.view_count * 0.1
        )
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Video unliked"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unliking video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlike video"
        )


@router.post("/videos/{video_id}/comments", status_code=status.HTTP_201_CREATED, response_model=CommentResponse)
async def create_comment(
    video_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CommentResponse:
    """
    Create a comment on a video post
    Requirements: 7.2
    
    Creates a Note object and wraps it in a Create activity for federated videos.
    
    Args:
        video_id: ID of the video to comment on
        comment_data: Comment content and optional parent comment ID
        
    Returns:
        Created comment
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create interaction service
        interaction_service = create_interaction_service(db)
        
        # Create comment
        result = await interaction_service.create_comment(
            user=current_user,
            video_post=video_post,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        comment = result["comment"]
        
        return CommentResponse(
            id=comment.id,
            video_post_id=comment.video_post_id,
            user_id=comment.user_id,
            content=comment.content,
            parent_comment_id=comment.parent_comment_id,
            is_federated=comment.is_federated,
            created_at=comment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )


@router.post("/videos/{video_id}/share", status_code=status.HTTP_200_OK)
async def share_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Share (Announce) a video post
    Requirements: 7.3
    
    Creates an Announce activity and delivers it to followers.
    
    Args:
        video_id: ID of the video to share
        
    Returns:
        Success message with activity info
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create interaction service
        interaction_service = create_interaction_service(db)
        
        # Create share
        result = await interaction_service.create_share(current_user, video_post)
        
        return {
            "status": "success",
            "message": "Video shared",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share video"
        )


@router.get("/videos/{video_id}/counts", status_code=status.HTTP_200_OK)
async def get_video_counts(
    video_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get aggregated interaction counts for a video
    Requirements: 7.8
    
    Returns counts from both local and federated sources.
    
    Args:
        video_id: ID of the video
        
    Returns:
        Aggregated counts (likes, comments, shares, views)
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create interaction service
        interaction_service = create_interaction_service(db)
        
        # Get aggregated counts
        counts = interaction_service.get_aggregated_counts(video_post)
        
        return counts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video counts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get video counts"
        )
