"""
Moderation Router
Handles content moderation endpoints
Requirements: 9.1-9.8
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, VideoPost, ModerationRecord
from app.services.moderation import create_moderation_service
from app.schemas import ModerationReview, ModerationRecordResponse, ModerationStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/moderation",
    tags=["moderation"]
)


# Placeholder for getting current user with moderator role
def get_current_moderator(db: Session = Depends(get_db)) -> User:
    """Get current authenticated moderator"""
    # For now, return a test user
    # In a real implementation, this would verify JWT and check for moderator role
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


@router.post("/videos/{video_id}/scan", status_code=status.HTTP_200_OK)
async def scan_video(
    video_id: int,
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_moderator)
) -> Dict[str, Any]:
    """
    Manually trigger moderation scan for a video
    Requirements: 9.1
    
    Args:
        video_id: ID of the video to scan
        
    Returns:
        Scan result
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create moderation service
        moderation_service = create_moderation_service(db)
        
        # Scan video
        result = await moderation_service.scan_video(
            video_post=video_post,
            video_path=video_post.original_file_path
        )
        
        return {
            "status": "success",
            "video_id": video_id,
            "scan_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scan video"
        )


@router.post("/videos/{video_id}/flag", status_code=status.HTTP_200_OK)
async def flag_video(
    video_id: int,
    reason: str,
    severity: str = "medium",
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_moderator)
) -> Dict[str, Any]:
    """
    Manually flag a video for policy violations
    Requirements: 9.2
    
    Args:
        video_id: ID of the video to flag
        reason: Reason for flagging
        severity: Severity level (low, medium, high)
        
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
        
        # Create moderation service
        moderation_service = create_moderation_service(db)
        
        # Flag content
        await moderation_service.flag_content(
            video_post=video_post,
            reason=reason,
            severity=severity
        )
        
        return {
            "status": "success",
            "message": "Video flagged",
            "video_id": video_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error flagging video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag video"
        )


@router.post("/videos/{video_id}/review", status_code=status.HTTP_200_OK)
async def review_video(
    video_id: int,
    review: ModerationReview,
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_moderator)
) -> Dict[str, Any]:
    """
    Review flagged content and take action
    Requirements: 9.4, 9.5
    
    Provides options to approve, reject, or delete content.
    
    Args:
        video_id: ID of the video to review
        review: Review action and optional reason
        
    Returns:
        Review result
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Create moderation service
        moderation_service = create_moderation_service(db)
        
        # Review content
        result = await moderation_service.review_flagged_content(
            video_post=video_post,
            action=review.action,
            reviewer=moderator,
            review_reason=review.reason
        )
        
        return {
            "status": "success",
            "video_id": video_id,
            "review_result": result
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review video"
        )


@router.get("/flagged", response_model=List[ModerationRecordResponse])
async def get_flagged_videos(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_moderator)
) -> List[ModerationRecordResponse]:
    """
    Get list of flagged videos for review
    Requirements: 9.4
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of flagged moderation records
    """
    try:
        # Query flagged moderation records
        records = db.query(ModerationRecord).filter(
            ModerationRecord.status == ModerationStatus.FLAGGED
        ).order_by(
            ModerationRecord.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [
            ModerationRecordResponse(
                id=record.id,
                video_post_id=record.video_post_id,
                status=record.status,
                reason=record.reason,
                severity=record.severity,
                reviewed_at=record.reviewed_at,
                created_at=record.created_at
            )
            for record in records
        ]
        
    except Exception as e:
        logger.error(f"Error getting flagged videos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get flagged videos"
        )


@router.get("/videos/{video_id}/status")
async def get_moderation_status(
    video_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get moderation status for a video
    
    Args:
        video_id: ID of the video
        
    Returns:
        Moderation status and records
    """
    try:
        # Find video post
        video_post = db.query(VideoPost).filter(VideoPost.id == video_id).first()
        if not video_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Get moderation records
        records = db.query(ModerationRecord).filter(
            ModerationRecord.video_post_id == video_id
        ).order_by(ModerationRecord.created_at.desc()).all()
        
        return {
            "video_id": video_id,
            "moderation_status": video_post.moderation_status,
            "moderation_reason": video_post.moderation_reason,
            "records": [
                {
                    "id": record.id,
                    "status": record.status,
                    "reason": record.reason,
                    "severity": record.severity,
                    "created_at": record.created_at.isoformat()
                }
                for record in records
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting moderation status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get moderation status"
        )
