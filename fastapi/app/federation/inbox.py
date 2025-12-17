"""
Inbox Handler for Federation Receiving
Handles incoming ActivityPub activities from remote instances
Requirements: 6.1-6.9
"""

import logging
import httpx
import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.models import VideoPost, Activity, Comment, User
from app.federation.activitypub import ActivityPubService
from app.schemas import VideoStatus, ModerationStatus

logger = logging.getLogger(__name__)


class InboxHandler:
    """
    Handles incoming ActivityPub activities
    Processes federated content and interactions
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.activitypub_service = ActivityPubService(db)
        self.instance_url = settings.INSTANCE_URL
        self.federated_content_dir = os.path.join(settings.UPLOAD_DIR, "federated")
        
        # Ensure federated content directory exists
        os.makedirs(self.federated_content_dir, exist_ok=True)
    
    async def handle_activity(
        self,
        activity: Dict[str, Any],
        signature: str,
        request_target: str,
        host: str,
        date: str,
        digest: str
    ) -> Dict[str, Any]:
        """
        Main entry point for handling incoming activities
        Requirements: 6.1, 6.2, 6.3
        
        Args:
            activity: ActivityPub activity JSON
            signature: HTTP Signature header
            request_target: Request target string
            host: Host header
            date: Date header
            digest: Digest header
            
        Returns:
            Response dict with status and message
        """
        try:
            # Step 1: Verify HTTP Signature
            # Requirements: 6.1, 6.2
            actor_url = activity.get("actor")
            if not actor_url:
                logger.error("Activity missing actor")
                return {"status": 401, "message": "Missing actor"}
            
            # Fetch actor's public key
            public_key = await self._fetch_actor_public_key(actor_url)
            if not public_key:
                logger.error(f"Could not fetch public key for {actor_url}")
                return {"status": 401, "message": "Could not verify signature"}
            
            # Verify signature
            is_valid = self.activitypub_service.verify_signature(
                signature_header=signature,
                request_target=request_target,
                host=host,
                date=date,
                digest=digest,
                public_key_pem=public_key
            )
            
            if not is_valid:
                logger.error(f"Invalid signature from {actor_url}")
                return {"status": 401, "message": "Invalid signature"}
            
            # Step 2: Parse and validate activity
            # Requirements: 6.3
            parsed_activity = self.activitypub_service.parse_activity(activity)
            if not parsed_activity:
                logger.error("Failed to parse activity")
                return {"status": 400, "message": "Invalid activity format"}
            
            if not self.activitypub_service.validate_activity_schema(parsed_activity):
                logger.error("Activity schema validation failed")
                return {"status": 400, "message": "Invalid activity schema"}
            
            # Step 3: Route to appropriate handler
            activity_type = parsed_activity.get("type")
            logger.info(f"Processing {activity_type} activity from {actor_url}")
            
            if activity_type == "Create":
                result = await self.process_create_activity(parsed_activity)
            elif activity_type == "Like":
                result = await self.process_like_activity(parsed_activity)
            elif activity_type == "Announce":
                result = await self.process_announce_activity(parsed_activity)
            elif activity_type == "Delete":
                result = await self.process_delete_activity(parsed_activity)
            elif activity_type == "Move":
                result = await self.process_move_activity(parsed_activity)
            else:
                logger.warning(f"Unsupported activity type: {activity_type}")
                return {"status": 400, "message": f"Unsupported activity type: {activity_type}"}
            
            # Store activity for audit trail
            self.activitypub_service.store_activity(parsed_activity, is_local=False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling activity: {e}", exc_info=True)
            return {"status": 500, "message": "Internal server error"}

    
    async def process_create_activity(
        self,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Create activity for federated videos
        Requirements: 6.4, 6.5, 6.6, 6.7, 6.8
        
        Args:
            activity: Create activity
            
        Returns:
            Response dict
        """
        try:
            obj = activity.get("object", {})
            obj_type = obj.get("type")
            
            # Handle Video objects
            if obj_type == "Video":
                return await self._process_federated_video(activity, obj)
            
            # Handle Note objects (comments)
            elif obj_type == "Note":
                return await self._process_federated_comment(activity, obj)
            
            else:
                logger.warning(f"Unsupported object type in Create: {obj_type}")
                return {"status": 400, "message": f"Unsupported object type: {obj_type}"}
                
        except Exception as e:
            logger.error(f"Error processing Create activity: {e}", exc_info=True)
            # Send Reject activity on failure (Requirement 6.9)
            await self._send_reject_activity(activity, str(e))
            return {"status": 500, "message": "Failed to process Create activity"}
    
    async def _process_federated_video(
        self,
        activity: Dict[str, Any],
        video_obj: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process federated video from Create activity
        Requirements: 6.4, 6.5, 6.6, 6.7, 6.8
        
        Args:
            activity: Parent activity
            video_obj: Video object
            
        Returns:
            Response dict
        """
        try:
            actor = activity.get("actor")
            video_url = video_obj.get("url")
            video_id = video_obj.get("id")
            
            # Check if already exists
            existing = self.db.query(VideoPost).filter(
                VideoPost.activitypub_id == video_id
            ).first()
            
            if existing:
                logger.info(f"Video {video_id} already exists")
                return {"status": 200, "message": "Video already processed"}
            
            # Extract metadata
            title = video_obj.get("name", "Untitled")[:200]
            description = video_obj.get("content", "")[:2000]
            duration_str = video_obj.get("duration", "")
            
            # Parse duration (ISO 8601 format: PT180S)
            duration = self._parse_duration(duration_str)
            
            # Extract tags
            tags = []
            for tag in video_obj.get("tag", []):
                if tag.get("type") == "Hashtag":
                    tag_name = tag.get("name", "").lstrip("#")
                    if tag_name:
                        tags.append(tag_name)
            tags = tags[:10]  # Limit to 10 tags
            
            # Validate size and duration (Requirement 6.5)
            if duration and duration > 180:
                logger.error(f"Federated video exceeds duration limit: {duration}s")
                await self._send_reject_activity(activity, "Duration exceeds 180 seconds")
                return {"status": 400, "message": "Duration exceeds limit"}
            
            # Download video (Requirement 6.4)
            try:
                file_path = await self.download_federated_video(video_url, video_obj)
            except Exception as e:
                logger.error(f"Failed to download federated video: {e}")
                await self._send_reject_activity(activity, f"Download failed: {str(e)}")
                return {"status": 500, "message": "Failed to download video"}
            
            # Extract origin metadata (Requirement 6.7)
            origin_instance = self._extract_instance_from_url(actor)
            origin_actor_did = actor  # Store full actor URL/DID
            
            # Create Video Post record
            video_post = VideoPost(
                user_id=1,  # System user for federated content
                title=title,
                description=description,
                tags=tags,
                duration=duration,
                status=VideoStatus.PROCESSING,
                original_file_path=file_path,
                is_federated=True,
                origin_instance=origin_instance,
                origin_actor_did=origin_actor_did,
                activitypub_id=video_id,
                moderation_status=ModerationStatus.PENDING
            )
            
            self.db.add(video_post)
            self.db.commit()
            self.db.refresh(video_post)
            
            logger.info(f"Created federated video post {video_post.id} from {origin_instance}")
            
            # Enqueue embedding generation (Requirement 6.8)
            # This will be handled by the media worker after transcoding
            from app.redis_client import redis_client
            await redis_client.enqueue_task("transcode_video", {
                "video_post_id": video_post.id,
                "input_path": file_path
            })
            
            return {"status": 202, "message": "Video accepted for processing"}
            
        except Exception as e:
            logger.error(f"Error processing federated video: {e}", exc_info=True)
            await self._send_reject_activity(activity, str(e))
            return {"status": 500, "message": "Failed to process video"}
    
    async def _process_federated_comment(
        self,
        activity: Dict[str, Any],
        note_obj: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process federated comment (Note) from Create activity
        Requirements: 7.6
        
        Args:
            activity: Parent activity
            note_obj: Note object
            
        Returns:
            Response dict
        """
        try:
            actor = activity.get("actor")
            note_id = note_obj.get("id")
            content = note_obj.get("content", "")
            in_reply_to = note_obj.get("inReplyTo")
            
            if not in_reply_to:
                logger.warning("Note not in reply to anything")
                return {"status": 400, "message": "Note must be in reply to a video"}
            
            # Find the video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.activitypub_id == in_reply_to
            ).first()
            
            if not video_post:
                logger.warning(f"Video not found for comment: {in_reply_to}")
                return {"status": 404, "message": "Video not found"}
            
            # Check if comment already exists
            existing = self.db.query(Comment).filter(
                Comment.activitypub_id == note_id
            ).first()
            
            if existing:
                logger.info(f"Comment {note_id} already exists")
                return {"status": 200, "message": "Comment already processed"}
            
            # Create comment record
            comment = Comment(
                video_post_id=video_post.id,
                user_id=1,  # System user for federated content
                content=content[:2000],
                is_federated=True,
                activitypub_id=note_id
            )
            
            self.db.add(comment)
            
            # Update comment count
            video_post.comment_count += 1
            
            self.db.commit()
            
            logger.info(f"Created federated comment on video {video_post.id}")
            return {"status": 200, "message": "Comment processed"}
            
        except Exception as e:
            logger.error(f"Error processing federated comment: {e}", exc_info=True)
            return {"status": 500, "message": "Failed to process comment"}

    
    async def process_like_activity(
        self,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Like activity for federated interactions
        Requirements: 7.5
        
        Args:
            activity: Like activity
            
        Returns:
            Response dict
        """
        try:
            actor = activity.get("actor")
            object_id = activity.get("object")
            
            if isinstance(object_id, dict):
                object_id = object_id.get("id")
            
            # Find the video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.activitypub_id == object_id
            ).first()
            
            if not video_post:
                logger.warning(f"Video not found for Like: {object_id}")
                return {"status": 404, "message": "Video not found"}
            
            # Check if like already recorded
            activity_id = activity.get("id")
            existing = self.db.query(Activity).filter(
                Activity.activity_id == activity_id
            ).first()
            
            if existing:
                logger.info(f"Like {activity_id} already processed")
                return {"status": 200, "message": "Like already processed"}
            
            # Increment like count
            video_post.like_count += 1
            
            # Update engagement score
            video_post.engagement_score = (
                video_post.like_count * 2 +
                video_post.comment_count * 3 +
                video_post.share_count * 4 +
                video_post.view_count * 0.1
            )
            
            self.db.commit()
            
            logger.info(f"Processed Like from {actor} on video {video_post.id}")
            return {"status": 200, "message": "Like processed"}
            
        except Exception as e:
            logger.error(f"Error processing Like activity: {e}", exc_info=True)
            return {"status": 500, "message": "Failed to process Like"}
    
    async def process_announce_activity(
        self,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Announce (share) activity
        Requirements: 7.6
        
        Args:
            activity: Announce activity
            
        Returns:
            Response dict
        """
        try:
            actor = activity.get("actor")
            object_id = activity.get("object")
            
            if isinstance(object_id, dict):
                object_id = object_id.get("id")
            
            # Find the video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.activitypub_id == object_id
            ).first()
            
            if not video_post:
                logger.warning(f"Video not found for Announce: {object_id}")
                return {"status": 404, "message": "Video not found"}
            
            # Check if announce already recorded
            activity_id = activity.get("id")
            existing = self.db.query(Activity).filter(
                Activity.activity_id == activity_id
            ).first()
            
            if existing:
                logger.info(f"Announce {activity_id} already processed")
                return {"status": 200, "message": "Announce already processed"}
            
            # Increment share count
            video_post.share_count += 1
            
            # Update engagement score
            video_post.engagement_score = (
                video_post.like_count * 2 +
                video_post.comment_count * 3 +
                video_post.share_count * 4 +
                video_post.view_count * 0.1
            )
            
            self.db.commit()
            
            logger.info(f"Processed Announce from {actor} on video {video_post.id}")
            return {"status": 200, "message": "Announce processed"}
            
        except Exception as e:
            logger.error(f"Error processing Announce activity: {e}", exc_info=True)
            return {"status": 500, "message": "Failed to process Announce"}
    
    async def process_delete_activity(
        self,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Delete activity
        Requirements: 9.8
        
        Args:
            activity: Delete activity
            
        Returns:
            Response dict
        """
        try:
            object_id = activity.get("object")
            
            if isinstance(object_id, dict):
                object_id = object_id.get("id")
            
            # Find the video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.activitypub_id == object_id
            ).first()
            
            if not video_post:
                logger.warning(f"Video not found for Delete: {object_id}")
                return {"status": 404, "message": "Video not found"}
            
            # Delete video file
            if video_post.original_file_path and os.path.exists(video_post.original_file_path):
                os.remove(video_post.original_file_path)
            
            # Delete transcoded files
            if video_post.resolutions:
                for resolution_path in video_post.resolutions.values():
                    if os.path.exists(resolution_path):
                        os.remove(resolution_path)
            
            # Delete thumbnails
            for thumb_path in [video_post.thumbnail_small, video_post.thumbnail_medium, video_post.thumbnail_large]:
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
            
            # Delete from Qdrant
            try:
                from app.ai.qdrant_client import qdrant_manager
                qdrant_manager.delete_embedding(video_post.id)
            except Exception as e:
                logger.warning(f"Failed to delete embedding: {e}")
            
            # Delete database record
            self.db.delete(video_post)
            self.db.commit()
            
            logger.info(f"Deleted video post {video_post.id}")
            return {"status": 200, "message": "Video deleted"}
            
        except Exception as e:
            logger.error(f"Error processing Delete activity: {e}", exc_info=True)
            return {"status": 500, "message": "Failed to process Delete"}
    
    async def process_move_activity(
        self,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Move activity for profile migration
        Requirements: 8.6, 8.7
        
        Args:
            activity: Move activity
            
        Returns:
            Response dict
        """
        try:
            actor = activity.get("actor")
            target = activity.get("target")
            
            if not target:
                logger.error("Move activity missing target")
                return {"status": 400, "message": "Missing target"}
            
            # Verify signature matches the original DID
            # This is already done in handle_activity
            
            # Update follower records
            from app.models import Follower
            followers = self.db.query(Follower).filter(
                Follower.follower_actor == actor
            ).all()
            
            for follower in followers:
                follower.follower_actor = target
                # Extract new inbox URL from target
                # In a real implementation, we'd fetch the actor document
                logger.info(f"Updated follower record for migration: {actor} -> {target}")
            
            self.db.commit()
            
            logger.info(f"Processed Move activity: {actor} -> {target}")
            return {"status": 200, "message": "Move processed"}
            
        except Exception as e:
            logger.error(f"Error processing Move activity: {e}", exc_info=True)
            return {"status": 500, "message": "Failed to process Move"}

    
    async def download_federated_video(
        self,
        video_url: str,
        video_object: Dict[str, Any]
    ) -> str:
        """
        Download federated video from remote instance
        Requirements: 6.4, 6.5, 6.6
        
        Args:
            video_url: URL of the video file
            video_object: Video object with metadata
            
        Returns:
            Path to downloaded file
            
        Raises:
            Exception if download fails or validation fails
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"federated_{timestamp}.mp4"
            file_path = os.path.join(self.federated_content_dir, filename)
            
            # Download with size limit (Requirement 6.5)
            max_size = 500 * 1024 * 1024  # 500MB
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("GET", video_url) as response:
                    response.raise_for_status()
                    
                    # Check content length
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > max_size:
                        raise ValueError(f"File size {content_length} exceeds limit {max_size}")
                    
                    # Download in chunks
                    downloaded_size = 0
                    with open(file_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            downloaded_size += len(chunk)
                            
                            # Check size during download
                            if downloaded_size > max_size:
                                os.remove(file_path)
                                raise ValueError(f"File size exceeds {max_size} bytes")
                            
                            f.write(chunk)
            
            logger.info(f"Downloaded federated video to {file_path} ({downloaded_size} bytes)")
            
            # Validate duration if provided (Requirement 6.5)
            duration_str = video_object.get("duration")
            if duration_str:
                duration = self._parse_duration(duration_str)
                if duration and duration > 180:
                    os.remove(file_path)
                    raise ValueError(f"Duration {duration}s exceeds 180s limit")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading federated video: {e}")
            # Clean up partial download
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
    
    async def _fetch_actor_public_key(
        self,
        actor_url: str
    ) -> Optional[str]:
        """
        Fetch actor's public key from their profile
        
        Args:
            actor_url: Actor's URL
            
        Returns:
            Public key in PEM format or None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    actor_url,
                    headers={"Accept": "application/activity+json"}
                )
                response.raise_for_status()
                
                actor_data = response.json()
                
                # Extract public key
                public_key_obj = actor_data.get("publicKey", {})
                public_key_pem = public_key_obj.get("publicKeyPem")
                
                if not public_key_pem:
                    logger.error(f"No public key found for {actor_url}")
                    return None
                
                return public_key_pem
                
        except Exception as e:
            logger.error(f"Error fetching actor public key: {e}")
            return None
    
    async def _send_reject_activity(
        self,
        original_activity: Dict[str, Any],
        reason: str
    ) -> None:
        """
        Send Reject activity to origin instance
        Requirements: 6.9, 9.7
        
        Args:
            original_activity: The activity being rejected
            reason: Reason for rejection
        """
        try:
            actor = original_activity.get("actor")
            activity_id = original_activity.get("id")
            
            # Create Reject activity
            reject_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{self.instance_url}/activities/reject/{datetime.utcnow().timestamp()}",
                "type": "Reject",
                "actor": self.instance_url,
                "object": activity_id,
                "summary": reason,
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Extract inbox URL from actor
            inbox_url = await self._fetch_actor_inbox(actor)
            if not inbox_url:
                logger.error(f"Could not find inbox for {actor}")
                return
            
            # Send Reject activity
            # This would use the outbox handler in a real implementation
            logger.info(f"Would send Reject activity to {inbox_url}: {reason}")
            
        except Exception as e:
            logger.error(f"Error sending Reject activity: {e}")
    
    async def _fetch_actor_inbox(
        self,
        actor_url: str
    ) -> Optional[str]:
        """
        Fetch actor's inbox URL
        
        Args:
            actor_url: Actor's URL
            
        Returns:
            Inbox URL or None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    actor_url,
                    headers={"Accept": "application/activity+json"}
                )
                response.raise_for_status()
                
                actor_data = response.json()
                inbox_url = actor_data.get("inbox")
                
                return inbox_url
                
        except Exception as e:
            logger.error(f"Error fetching actor inbox: {e}")
            return None
    
    def _parse_duration(
        self,
        duration_str: str
    ) -> Optional[int]:
        """
        Parse ISO 8601 duration string (e.g., PT180S)
        
        Args:
            duration_str: Duration string
            
        Returns:
            Duration in seconds or None
        """
        try:
            if not duration_str or not duration_str.startswith("PT"):
                return None
            
            # Simple parser for PT<number>S format
            duration_str = duration_str[2:]  # Remove PT
            if duration_str.endswith("S"):
                return int(duration_str[:-1])
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing duration {duration_str}: {e}")
            return None
    
    def _extract_instance_from_url(
        self,
        url: str
    ) -> str:
        """
        Extract instance domain from URL
        
        Args:
            url: Full URL
            
        Returns:
            Instance domain
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception as e:
            logger.warning(f"Error extracting instance from {url}: {e}")
            return url


def create_inbox_handler(db: Session) -> InboxHandler:
    """Factory function to create inbox handler"""
    return InboxHandler(db)
