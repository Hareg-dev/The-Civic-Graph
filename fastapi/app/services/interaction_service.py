"""
Interaction Service for Federated Interactions
Handles likes, comments, and shares on both local and federated content
Requirements: 7.1-7.8
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.models import VideoPost, User, UserInteraction, Comment, Activity
from app.federation.activitypub import ActivityPubService

logger = logging.getLogger(__name__)


class InteractionService:
    """
    Service for handling user interactions with videos
    Supports both local and federated content
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.activitypub_service = ActivityPubService(db)
        self.instance_url = settings.INSTANCE_URL
    
    async def create_like(
        self,
        user: User,
        video_post: VideoPost
    ) -> Dict[str, Any]:
        """
        Create a Like activity for a video post
        Requirements: 7.1
        
        Args:
            user: User performing the like
            video_post: Video being liked
            
        Returns:
            Result dict with activity info
        """
        try:
            # Check if already liked
            existing = self.db.query(UserInteraction).filter(
                UserInteraction.user_id == user.id,
                UserInteraction.video_post_id == video_post.id,
                UserInteraction.interaction_type == "like"
            ).first()
            
            if existing:
                logger.info(f"User {user.id} already liked video {video_post.id}")
                return {"status": "already_liked", "activity": None}
            
            # Create local interaction record
            interaction = UserInteraction(
                user_id=user.id,
                video_post_id=video_post.id,
                interaction_type="like",
                created_at=datetime.utcnow()
            )
            self.db.add(interaction)
            
            # Update video post like count
            video_post.like_count += 1
            
            # Update engagement score
            video_post.engagement_score = (
                video_post.like_count * 2 +
                video_post.comment_count * 3 +
                video_post.share_count * 4 +
                video_post.view_count * 0.1
            )
            
            self.db.commit()
            
            # If video is federated, create and deliver Like activity
            # Requirements: 7.1, 7.4
            if video_post.is_federated and video_post.activitypub_id:
                activity = await self._create_like_activity(user, video_post)
                
                # Enqueue delivery to origin instance
                await self._enqueue_delivery(activity, video_post.origin_instance)
                
                logger.info(f"Created Like activity for federated video {video_post.id}")
                return {"status": "liked", "activity": activity}
            
            logger.info(f"User {user.id} liked local video {video_post.id}")
            return {"status": "liked", "activity": None}
            
        except Exception as e:
            logger.error(f"Error creating like: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def create_comment(
        self,
        user: User,
        video_post: VideoPost,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a comment (Note) on a video post
        Requirements: 7.2
        
        Args:
            user: User creating the comment
            video_post: Video being commented on
            content: Comment text
            parent_comment_id: Optional parent comment for replies
            
        Returns:
            Result dict with comment and activity info
        """
        try:
            # Create comment record
            comment = Comment(
                video_post_id=video_post.id,
                user_id=user.id,
                content=content[:2000],
                parent_comment_id=parent_comment_id,
                is_federated=False,
                created_at=datetime.utcnow()
            )
            
            # Generate ActivityPub ID for the comment
            comment.activitypub_id = f"{self.instance_url}/comments/{datetime.utcnow().timestamp()}"
            
            self.db.add(comment)
            
            # Update video post comment count
            video_post.comment_count += 1
            
            # Update engagement score
            video_post.engagement_score = (
                video_post.like_count * 2 +
                video_post.comment_count * 3 +
                video_post.share_count * 4 +
                video_post.view_count * 0.1
            )
            
            self.db.commit()
            self.db.refresh(comment)
            
            # If video is federated, create and deliver Create(Note) activity
            # Requirements: 7.2, 7.4
            if video_post.is_federated and video_post.activitypub_id:
                activity = await self._create_comment_activity(user, video_post, comment)
                
                # Enqueue delivery to origin instance
                await self._enqueue_delivery(activity, video_post.origin_instance)
                
                logger.info(f"Created Comment activity for federated video {video_post.id}")
                return {"status": "commented", "comment": comment, "activity": activity}
            
            logger.info(f"User {user.id} commented on local video {video_post.id}")
            return {"status": "commented", "comment": comment, "activity": None}
            
        except Exception as e:
            logger.error(f"Error creating comment: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def create_share(
        self,
        user: User,
        video_post: VideoPost
    ) -> Dict[str, Any]:
        """
        Create a Share (Announce) activity for a video post
        Requirements: 7.3
        
        Args:
            user: User sharing the video
            video_post: Video being shared
            
        Returns:
            Result dict with activity info
        """
        try:
            # Create local interaction record
            interaction = UserInteraction(
                user_id=user.id,
                video_post_id=video_post.id,
                interaction_type="share",
                created_at=datetime.utcnow()
            )
            self.db.add(interaction)
            
            # Update video post share count
            video_post.share_count += 1
            
            # Update engagement score
            video_post.engagement_score = (
                video_post.like_count * 2 +
                video_post.comment_count * 3 +
                video_post.share_count * 4 +
                video_post.view_count * 0.1
            )
            
            self.db.commit()
            
            # Create Announce activity
            # Requirements: 7.3, 7.4
            activity = await self._create_announce_activity(user, video_post)
            
            # If video is federated, deliver to origin instance
            if video_post.is_federated and video_post.origin_instance:
                await self._enqueue_delivery(activity, video_post.origin_instance)
            
            # Also deliver to user's followers
            await self._deliver_to_followers(user, activity)
            
            logger.info(f"User {user.id} shared video {video_post.id}")
            return {"status": "shared", "activity": activity}
            
        except Exception as e:
            logger.error(f"Error creating share: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def get_aggregated_counts(
        self,
        video_post: VideoPost
    ) -> Dict[str, int]:
        """
        Get aggregated interaction counts from local and federated sources
        Requirements: 7.8
        
        Args:
            video_post: Video post to get counts for
            
        Returns:
            Dict with aggregated counts
        """
        try:
            # Local counts are already stored in the video_post model
            # In a full implementation, we would also query federated activities
            # For now, return the stored counts which include both local and federated
            
            return {
                "likes": video_post.like_count,
                "comments": video_post.comment_count,
                "shares": video_post.share_count,
                "views": video_post.view_count,
                "engagement_score": video_post.engagement_score
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregated counts: {e}", exc_info=True)
            return {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "views": 0,
                "engagement_score": 0.0
            }

    
    async def _create_like_activity(
        self,
        user: User,
        video_post: VideoPost
    ) -> Dict[str, Any]:
        """
        Create a Like activity for federation
        Requirements: 7.1, 7.4
        
        Args:
            user: User performing the like
            video_post: Video being liked
            
        Returns:
            Like activity
        """
        try:
            actor_id = f"{self.instance_url}/users/{user.username}"
            
            activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{self.instance_url}/activities/like/{datetime.utcnow().timestamp()}",
                "type": "Like",
                "actor": actor_id,
                "object": video_post.activitypub_id,
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Store activity
            self.activitypub_service.store_activity(activity, is_local=True)
            
            return activity
            
        except Exception as e:
            logger.error(f"Error creating Like activity: {e}")
            raise
    
    async def _create_comment_activity(
        self,
        user: User,
        video_post: VideoPost,
        comment: Comment
    ) -> Dict[str, Any]:
        """
        Create a Create(Note) activity for a comment
        Requirements: 7.2, 7.4
        
        Args:
            user: User creating the comment
            video_post: Video being commented on
            comment: Comment object
            
        Returns:
            Create activity with Note object
        """
        try:
            actor_id = f"{self.instance_url}/users/{user.username}"
            
            # Create Note object
            note = {
                "id": comment.activitypub_id,
                "type": "Note",
                "attributedTo": actor_id,
                "content": comment.content,
                "inReplyTo": video_post.activitypub_id,
                "published": comment.created_at.isoformat() + "Z"
            }
            
            # Wrap in Create activity
            activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{self.instance_url}/activities/create/{datetime.utcnow().timestamp()}",
                "type": "Create",
                "actor": actor_id,
                "object": note,
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Store activity
            self.activitypub_service.store_activity(activity, is_local=True)
            
            return activity
            
        except Exception as e:
            logger.error(f"Error creating Comment activity: {e}")
            raise
    
    async def _create_announce_activity(
        self,
        user: User,
        video_post: VideoPost
    ) -> Dict[str, Any]:
        """
        Create an Announce activity for a share
        Requirements: 7.3, 7.4
        
        Args:
            user: User sharing the video
            video_post: Video being shared
            
        Returns:
            Announce activity
        """
        try:
            actor_id = f"{self.instance_url}/users/{user.username}"
            
            # Use ActivityPub ID if available, otherwise create local URL
            object_id = video_post.activitypub_id or f"{self.instance_url}/videos/{video_post.id}"
            
            activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{self.instance_url}/activities/announce/{datetime.utcnow().timestamp()}",
                "type": "Announce",
                "actor": actor_id,
                "object": object_id,
                "published": datetime.utcnow().isoformat() + "Z",
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "cc": [f"{actor_id}/followers"]
            }
            
            # Store activity
            self.activitypub_service.store_activity(activity, is_local=True)
            
            return activity
            
        except Exception as e:
            logger.error(f"Error creating Announce activity: {e}")
            raise
    
    async def _enqueue_delivery(
        self,
        activity: Dict[str, Any],
        target_instance: Optional[str]
    ) -> None:
        """
        Enqueue activity for delivery to a remote instance
        
        Args:
            activity: Activity to deliver
            target_instance: Target instance URL
        """
        try:
            if not target_instance:
                logger.warning("No target instance for delivery")
                return
            
            # In a full implementation, this would use the outbox handler
            # For now, we'll use Redis to enqueue the delivery task
            from app.redis_client import redis_client
            
            await redis_client.enqueue_task("deliver_activity", {
                "activity": activity,
                "target_instance": target_instance
            })
            
            logger.info(f"Enqueued delivery to {target_instance}")
            
        except Exception as e:
            logger.error(f"Error enqueueing delivery: {e}")
    
    async def _deliver_to_followers(
        self,
        user: User,
        activity: Dict[str, Any]
    ) -> None:
        """
        Deliver activity to user's followers
        
        Args:
            user: User whose followers should receive the activity
            activity: Activity to deliver
        """
        try:
            # Get user's followers
            from app.models import Follower
            followers = self.db.query(Follower).filter(
                Follower.user_id == user.id
            ).all()
            
            # Enqueue delivery to each follower's inbox
            for follower in followers:
                if not follower.is_local:
                    await redis_client.enqueue_task("deliver_activity", {
                        "activity": activity,
                        "inbox_url": follower.follower_inbox
                    })
            
            logger.info(f"Enqueued delivery to {len(followers)} followers")
            
        except Exception as e:
            logger.error(f"Error delivering to followers: {e}")


def create_interaction_service(db: Session) -> InteractionService:
    """Factory function to create interaction service"""
    return InteractionService(db)
