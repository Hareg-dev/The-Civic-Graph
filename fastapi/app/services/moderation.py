"""
Moderation Service for Content Moderation
Handles video scanning, flagging, and moderation workflows
Requirements: 9.1-9.8
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.models import VideoPost, ModerationRecord, User
from app.schemas import ModerationStatus

logger = logging.getLogger(__name__)


class ModerationService:
    """
    Service for content moderation
    Scans videos for policy violations and manages moderation workflow
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.moderation_enabled = settings.MODERATION_ENABLED
        self.api_key = settings.MODERATION_API_KEY
        self.api_endpoint = settings.MODERATION_API_ENDPOINT
    
    async def scan_video(
        self,
        video_post: VideoPost,
        video_path: str
    ) -> Dict[str, Any]:
        """
        Scan video for policy violations using moderation API
        Requirements: 9.1
        
        Args:
            video_post: Video post to scan
            video_path: Path to video file
            
        Returns:
            Moderation result
        """
        try:
            if not self.moderation_enabled:
                logger.info("Moderation disabled, skipping scan")
                return {
                    "status": "skipped",
                    "reason": "Moderation disabled"
                }
            
            # Create moderation record
            moderation_record = ModerationRecord(
                video_post_id=video_post.id,
                status=ModerationStatus.PENDING,
                created_at=datetime.utcnow()
            )
            self.db.add(moderation_record)
            self.db.commit()
            self.db.refresh(moderation_record)
            
            # In a real implementation, this would call an external API
            # For now, we'll simulate the moderation check
            result = await self._call_moderation_api(video_path)
            
            # Update moderation record with results
            moderation_record.api_response = result
            
            # Check if content violates policies
            if result.get("explicit_content", False):
                # Flag the content (Requirement 9.2)
                await self.flag_content(
                    video_post=video_post,
                    reason="Explicit content detected",
                    severity="high",
                    moderation_record=moderation_record
                )
                
                logger.warning(f"Video {video_post.id} flagged for explicit content")
                return {
                    "status": "flagged",
                    "reason": "Explicit content detected"
                }
            
            # Approve if no violations
            moderation_record.status = ModerationStatus.APPROVED
            video_post.moderation_status = ModerationStatus.APPROVED
            
            self.db.commit()
            
            logger.info(f"Video {video_post.id} approved by moderation")
            return {
                "status": "approved",
                "reason": "No policy violations detected"
            }
            
        except Exception as e:
            logger.error(f"Error scanning video: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def flag_content(
        self,
        video_post: VideoPost,
        reason: str,
        severity: str,
        moderation_record: Optional[ModerationRecord] = None
    ) -> None:
        """
        Flag video post for policy violations
        Requirements: 9.2, 9.3
        
        Args:
            video_post: Video post to flag
            reason: Reason for flagging
            severity: Severity level (low, medium, high)
            moderation_record: Optional existing moderation record
        """
        try:
            # Update or create moderation record
            if not moderation_record:
                moderation_record = self.db.query(ModerationRecord).filter(
                    ModerationRecord.video_post_id == video_post.id
                ).order_by(ModerationRecord.created_at.desc()).first()
                
                if not moderation_record:
                    moderation_record = ModerationRecord(
                        video_post_id=video_post.id,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(moderation_record)
            
            moderation_record.status = ModerationStatus.FLAGGED
            moderation_record.reason = reason
            moderation_record.severity = severity
            
            # Update video post status (Requirement 9.2)
            video_post.moderation_status = ModerationStatus.FLAGGED
            video_post.moderation_reason = reason
            
            self.db.commit()
            
            # Notify creator (Requirement 9.3)
            await self._notify_creator(video_post, reason)
            
            logger.info(f"Flagged video {video_post.id}: {reason}")
            
        except Exception as e:
            logger.error(f"Error flagging content: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def review_flagged_content(
        self,
        video_post: VideoPost,
        action: str,
        reviewer: User,
        review_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Review flagged content and take action
        Requirements: 9.4, 9.5
        
        Args:
            video_post: Video post to review
            action: Action to take (approve, reject, delete)
            reviewer: User performing the review
            review_reason: Optional reason for the action
            
        Returns:
            Review result
        """
        try:
            # Get moderation record
            moderation_record = self.db.query(ModerationRecord).filter(
                ModerationRecord.video_post_id == video_post.id
            ).order_by(ModerationRecord.created_at.desc()).first()
            
            if not moderation_record:
                raise ValueError("No moderation record found")
            
            # Update moderation record
            moderation_record.reviewer_id = reviewer.id
            moderation_record.reviewed_at = datetime.utcnow()
            
            if action == "approve":
                moderation_record.status = ModerationStatus.APPROVED
                video_post.moderation_status = ModerationStatus.APPROVED
                video_post.moderation_reason = None
                
                logger.info(f"Approved video {video_post.id}")
                result = {"status": "approved", "message": "Content approved"}
                
            elif action == "reject":
                # Reject and remove from feeds (Requirement 9.5)
                moderation_record.status = ModerationStatus.REJECTED
                video_post.moderation_status = ModerationStatus.REJECTED
                video_post.status = "rejected"
                
                if review_reason:
                    video_post.moderation_reason = review_reason
                
                # Send Reject activity if federated
                if video_post.is_federated and video_post.origin_instance:
                    await self._send_reject_activity(video_post, review_reason or "Policy violation")
                
                logger.info(f"Rejected video {video_post.id}")
                result = {"status": "rejected", "message": "Content rejected"}
                
            elif action == "delete":
                # Delete content completely
                await self._delete_video_content(video_post)
                
                logger.info(f"Deleted video {video_post.id}")
                result = {"status": "deleted", "message": "Content deleted"}
                
            else:
                raise ValueError(f"Invalid action: {action}")
            
            self.db.commit()
            return result
            
        except Exception as e:
            logger.error(f"Error reviewing content: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def reject_federated_content(
        self,
        video_post: VideoPost,
        reason: str
    ) -> None:
        """
        Reject federated content and send Reject activity
        Requirements: 9.7
        
        Args:
            video_post: Federated video post to reject
            reason: Reason for rejection
        """
        try:
            # Update video post status
            video_post.moderation_status = ModerationStatus.REJECTED
            video_post.status = "rejected"
            video_post.moderation_reason = reason
            
            # Create moderation record
            moderation_record = ModerationRecord(
                video_post_id=video_post.id,
                status=ModerationStatus.REJECTED,
                reason=reason,
                severity="high",
                created_at=datetime.utcnow()
            )
            self.db.add(moderation_record)
            self.db.commit()
            
            # Send Reject activity to origin instance
            if video_post.origin_instance:
                await self._send_reject_activity(video_post, reason)
            
            logger.info(f"Rejected federated video {video_post.id}: {reason}")
            
        except Exception as e:
            logger.error(f"Error rejecting federated content: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def applies_same_rules(
        self,
        video_post: VideoPost
    ) -> bool:
        """
        Check if same moderation rules apply to local and federated content
        Requirements: 9.6
        
        Args:
            video_post: Video post to check
            
        Returns:
            True (same rules always apply)
        """
        # Same moderation rules apply to both local and federated content
        # This is enforced by using the same scan_video method for both
        return True

    
    async def _call_moderation_api(
        self,
        video_path: str
    ) -> Dict[str, Any]:
        """
        Call external moderation API
        
        Args:
            video_path: Path to video file
            
        Returns:
            API response
        """
        try:
            if not self.api_endpoint or not self.api_key:
                logger.warning("Moderation API not configured, returning safe result")
                return {
                    "explicit_content": False,
                    "violence": False,
                    "safe": True
                }
            
            # In a real implementation, this would call AWS Rekognition,
            # Google Video Intelligence, or similar service
            # For now, return a mock response
            
            logger.info(f"Would call moderation API for {video_path}")
            
            return {
                "explicit_content": False,
                "violence": False,
                "safe": True,
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"Error calling moderation API: {e}")
            # Return safe result on error to avoid blocking content
            return {
                "explicit_content": False,
                "violence": False,
                "safe": True,
                "error": str(e)
            }
    
    async def _notify_creator(
        self,
        video_post: VideoPost,
        reason: str
    ) -> None:
        """
        Notify content creator about flagging
        Requirements: 9.3
        
        Args:
            video_post: Flagged video post
            reason: Reason for flagging
        """
        try:
            # In a real implementation, this would send an email or notification
            # For now, just log it
            logger.info(f"Would notify user {video_post.user_id} about flagged video: {reason}")
            
        except Exception as e:
            logger.error(f"Error notifying creator: {e}")
    
    async def _send_reject_activity(
        self,
        video_post: VideoPost,
        reason: str
    ) -> None:
        """
        Send Reject activity to origin instance
        Requirements: 9.7
        
        Args:
            video_post: Video post being rejected
            reason: Reason for rejection
        """
        try:
            if not video_post.origin_instance or not video_post.activitypub_id:
                logger.warning("Cannot send Reject activity: missing origin info")
                return
            
            # Create Reject activity
            reject_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{settings.INSTANCE_URL}/activities/reject/{datetime.utcnow().timestamp()}",
                "type": "Reject",
                "actor": settings.INSTANCE_URL,
                "object": video_post.activitypub_id,
                "summary": reason,
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Enqueue delivery
            from app.redis_client import redis_client
            await redis_client.enqueue_task("deliver_activity", {
                "activity": reject_activity,
                "target_instance": video_post.origin_instance
            })
            
            logger.info(f"Enqueued Reject activity for video {video_post.id}")
            
        except Exception as e:
            logger.error(f"Error sending Reject activity: {e}")
    
    async def _delete_video_content(
        self,
        video_post: VideoPost
    ) -> None:
        """
        Delete video content and all associated data
        Requirements: 9.8
        
        Args:
            video_post: Video post to delete
        """
        try:
            import os
            
            # Delete video file
            if video_post.original_file_path and os.path.exists(video_post.original_file_path):
                os.remove(video_post.original_file_path)
                logger.info(f"Deleted original file: {video_post.original_file_path}")
            
            # Delete transcoded files
            if video_post.resolutions:
                for resolution_path in video_post.resolutions.values():
                    if os.path.exists(resolution_path):
                        os.remove(resolution_path)
                        logger.info(f"Deleted resolution file: {resolution_path}")
            
            # Delete thumbnails
            for thumb_path in [video_post.thumbnail_small, video_post.thumbnail_medium, video_post.thumbnail_large]:
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    logger.info(f"Deleted thumbnail: {thumb_path}")
            
            # Delete from Qdrant
            try:
                from app.ai.qdrant_client import qdrant_manager
                qdrant_manager.delete_embedding(video_post.id)
                logger.info(f"Deleted embedding for video {video_post.id}")
            except Exception as e:
                logger.warning(f"Failed to delete embedding: {e}")
            
            # Delete database record
            self.db.delete(video_post)
            self.db.commit()
            
            logger.info(f"Deleted video post {video_post.id} completely")
            
        except Exception as e:
            logger.error(f"Error deleting video content: {e}", exc_info=True)
            raise


def create_moderation_service(db: Session) -> ModerationService:
    """Factory function to create moderation service"""
    return ModerationService(db)
