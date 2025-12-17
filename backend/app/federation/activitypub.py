"""
ActivityPub Service for Federation
Handles creation, signing, and validation of ActivityPub activities
Requirements: 5.1-5.4, 6.1-6.3
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import base64
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

from sqlalchemy.orm import Session
from app.config import settings
from app.models import VideoPost, User, Activity
from app.schemas import ActivityPubObject

logger = logging.getLogger(__name__)


class ActivityPubService:
    """
    Service for creating and managing ActivityPub activities
    Implements ActivityPub specification for federation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.instance_url = settings.INSTANCE_URL
    
    def create_video_object(
        self,
        video_post: VideoPost,
        user: User
    ) -> Dict[str, Any]:
        """
        Create ActivityPub object for a Video Post
        Requirements: 5.1, 5.2
        
        Args:
            video_post: Video post to convert
            user: Owner of the video post
            
        Returns:
            ActivityPub Video object
        """
        try:
            # Generate ActivityPub ID if not exists
            if not video_post.activitypub_id:
                video_post.activitypub_id = f"{self.instance_url}/videos/{video_post.id}"
                self.db.commit()
            
            # Build video object
            video_object = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": video_post.activitypub_id,
                "type": "Video",
                "name": video_post.title,
                "content": video_post.description or "",
                "published": video_post.created_at.isoformat() + "Z",
                "attributedTo": f"{self.instance_url}/users/{user.username}",
                "duration": f"PT{video_post.duration}S" if video_post.duration else None,
                "url": video_post.activitypub_id,
                "mediaType": "video/mp4",
                "tag": [{"type": "Hashtag", "name": f"#{tag}"} for tag in (video_post.tags or [])],
            }
            
            # Add resolution attachments
            attachments = self._create_resolution_attachments(video_post)
            if attachments:
                video_object["attachment"] = attachments
            
            # Add thumbnail
            if video_post.thumbnail_large:
                video_object["icon"] = {
                    "type": "Image",
                    "mediaType": "image/jpeg",
                    "url": f"{self.instance_url}/{video_post.thumbnail_large}"
                }
            
            logger.info(f"Created ActivityPub object for video {video_post.id}")
            return video_object
            
        except Exception as e:
            logger.error(f"Error creating video object: {e}")
            raise
    
    def _create_resolution_attachments(
        self,
        video_post: VideoPost
    ) -> List[Dict[str, Any]]:
        """
        Create attachment objects for resolution variants
        Requirements: 5.3
        
        Args:
            video_post: Video post with resolutions
            
        Returns:
            List of attachment objects
        """
        attachments = []
        
        if not video_post.resolutions:
            return attachments
        
        # Resolution order and dimensions
        resolution_info = {
            "360p": {"width": 640, "height": 360},
            "480p": {"width": 854, "height": 480},
            "720p": {"width": 1280, "height": 720},
            "1080p": {"width": 1920, "height": 1080}
        }
        
        for resolution, file_path in video_post.resolutions.items():
            if resolution in resolution_info:
                info = resolution_info[resolution]
                attachment = {
                    "type": "Document",
                    "mediaType": "video/mp4",
                    "url": f"{self.instance_url}/{file_path}",
                    "name": f"{resolution} version",
                    "width": info["width"],
                    "height": info["height"]
                }
                attachments.append(attachment)
        
        return attachments
    
    def create_activity(
        self,
        activity_type: str,
        actor: str,
        object_data: Dict[str, Any],
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an ActivityPub activity
        Requirements: 5.1, 5.2
        
        Args:
            activity_type: Type of activity (Create, Like, Announce, etc.)
            actor: Actor performing the activity
            object_data: The object being acted upon
            additional_fields: Additional activity fields
            
        Returns:
            Complete ActivityPub activity
        """
        try:
            # Generate activity ID
            activity_id = f"{self.instance_url}/activities/{datetime.utcnow().timestamp()}"
            
            activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": activity_id,
                "type": activity_type,
                "actor": actor,
                "object": object_data,
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Add additional fields
            if additional_fields:
                activity.update(additional_fields)
            
            logger.info(f"Created {activity_type} activity: {activity_id}")
            return activity
            
        except Exception as e:
            logger.error(f"Error creating activity: {e}")
            raise
    
    def create_create_activity(
        self,
        video_post: VideoPost,
        user: User
    ) -> Dict[str, Any]:
        """
        Create a Create activity for a new video post
        Requirements: 5.1, 5.2
        
        Args:
            video_post: Video post to announce
            user: User who created the video
            
        Returns:
            Create activity
        """
        try:
            # Create video object
            video_object = self.create_video_object(video_post, user)
            
            # Create activity
            actor_id = f"{self.instance_url}/users/{user.username}"
            activity = self.create_activity(
                activity_type="Create",
                actor=actor_id,
                object_data=video_object,
                additional_fields={
                    "to": ["https://www.w3.org/ns/activitystreams#Public"],
                    "cc": [f"{actor_id}/followers"]
                }
            )
            
            logger.info(f"Created Create activity for video {video_post.id}")
            return activity
            
        except Exception as e:
            logger.error(f"Error creating Create activity: {e}")
            raise
    
    def sign_activity(
        self,
        activity: Dict[str, Any],
        private_key_pem: str,
        key_id: str
    ) -> str:
        """
        Sign an ActivityPub activity using HTTP Signatures
        Requirements: 5.4
        
        Args:
            activity: Activity to sign
            private_key_pem: Private key in PEM format
            key_id: Key identifier URL
            
        Returns:
            Signature header value
        """
        try:
            # Serialize activity
            activity_json = json.dumps(activity, sort_keys=True)
            
            # Create digest
            digest = hashlib.sha256(activity_json.encode()).digest()
            digest_b64 = base64.b64encode(digest).decode()
            
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Create signature string
            date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            signature_string = f"(request-target): post /inbox\nhost: {urlparse(self.instance_url).netloc}\ndate: {date}\ndigest: SHA-256={digest_b64}"
            
            # Sign
            signature = private_key.sign(
                signature_string.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            signature_b64 = base64.b64encode(signature).decode()
            
            # Build signature header
            signature_header = (
                f'keyId="{key_id}",'
                f'algorithm="rsa-sha256",'
                f'headers="(request-target) host date digest",'
                f'signature="{signature_b64}"'
            )
            
            logger.info(f"Signed activity with key {key_id}")
            return signature_header
            
        except Exception as e:
            logger.error(f"Error signing activity: {e}")
            raise
    
    def verify_signature(
        self,
        signature_header: str,
        request_target: str,
        host: str,
        date: str,
        digest: str,
        public_key_pem: str
    ) -> bool:
        """
        Verify HTTP Signature on incoming activity
        Requirements: 6.1, 6.2
        
        Args:
            signature_header: Signature header value
            request_target: Request target (e.g., "post /inbox")
            host: Host header value
            date: Date header value
            digest: Digest header value
            public_key_pem: Public key in PEM format
            
        Returns:
            True if signature is valid
        """
        try:
            # Parse signature header
            sig_parts = {}
            for part in signature_header.split(","):
                key, value = part.split("=", 1)
                sig_parts[key.strip()] = value.strip('""')
            
            # Extract signature
            signature_b64 = sig_parts.get("signature")
            if not signature_b64:
                logger.error("No signature in header")
                return False
            
            signature = base64.b64decode(signature_b64)
            
            # Reconstruct signature string
            headers = sig_parts.get("headers", "").split()
            signature_parts = []
            
            for header in headers:
                if header == "(request-target)":
                    signature_parts.append(f"(request-target): {request_target}")
                elif header == "host":
                    signature_parts.append(f"host: {host}")
                elif header == "date":
                    signature_parts.append(f"date: {date}")
                elif header == "digest":
                    signature_parts.append(f"digest: {digest}")
            
            signature_string = "\n".join(signature_parts)
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Verify signature
            try:
                public_key.verify(
                    signature,
                    signature_string.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                logger.info("Signature verification successful")
                return True
            except Exception as e:
                logger.error(f"Signature verification failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    def parse_activity(
        self,
        activity_json: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse and validate ActivityPub activity
        Requirements: 6.3
        
        Args:
            activity_json: Raw activity JSON
            
        Returns:
            Parsed activity or None if invalid
        """
        try:
            # Validate required fields
            required_fields = ["@context", "type", "actor"]
            for field in required_fields:
                if field not in activity_json:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Validate activity type
            valid_types = ["Create", "Like", "Announce", "Delete", "Move", "Follow", "Accept", "Reject"]
            if activity_json["type"] not in valid_types:
                logger.error(f"Invalid activity type: {activity_json['type']}")
                return None
            
            # Validate context
            if activity_json["@context"] != "https://www.w3.org/ns/activitystreams":
                logger.warning(f"Non-standard context: {activity_json['@context']}")
            
            logger.info(f"Parsed {activity_json['type']} activity from {activity_json['actor']}")
            return activity_json
            
        except Exception as e:
            logger.error(f"Error parsing activity: {e}")
            return None
    
    def validate_activity_schema(
        self,
        activity: Dict[str, Any]
    ) -> bool:
        """
        Validate activity against ActivityPub schema
        Requirements: 6.3
        
        Args:
            activity: Activity to validate
            
        Returns:
            True if valid
        """
        try:
            # Check for required fields based on type
            activity_type = activity.get("type")
            
            if activity_type in ["Create", "Update", "Delete"]:
                if "object" not in activity:
                    logger.error(f"{activity_type} activity missing object")
                    return False
            
            if activity_type == "Follow":
                if "object" not in activity:
                    logger.error("Follow activity missing object")
                    return False
            
            # Validate actor format
            actor = activity.get("actor")
            if not actor or not isinstance(actor, str):
                logger.error("Invalid actor format")
                return False
            
            # Validate ID format
            activity_id = activity.get("id")
            if activity_id and not isinstance(activity_id, str):
                logger.error("Invalid id format")
                return False
            
            logger.info(f"Activity schema validation passed for {activity_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating activity schema: {e}")
            return False
    
    def store_activity(
        self,
        activity: Dict[str, Any],
        is_local: bool = True
    ) -> Optional[Activity]:
        """
        Store activity in database
        
        Args:
            activity: Activity to store
            is_local: Whether activity originated locally
            
        Returns:
            Activity record or None
        """
        try:
            activity_record = Activity(
                activity_id=activity.get("id", ""),
                activity_type=activity.get("type", ""),
                actor=activity.get("actor", ""),
                object_id=str(activity.get("object", {}).get("id", "")),
                object_type=activity.get("object", {}).get("type", ""),
                content=activity,
                is_local=is_local,
                created_at=datetime.utcnow()
            )
            
            self.db.add(activity_record)
            self.db.commit()
            
            logger.info(f"Stored activity {activity_record.id}")
            return activity_record
            
        except Exception as e:
            logger.error(f"Error storing activity: {e}")
            self.db.rollback()
            return None


def create_activitypub_service(db: Session) -> ActivityPubService:
    """Factory function to create ActivityPub service"""
    return ActivityPubService(db)
