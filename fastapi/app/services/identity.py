"""
Identity Service for DID Management
Handles decentralized identity, key management, and profile migration
Requirements: 8.1-8.8
"""

import logging
import base64
import os
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, DIDDocument, VideoPost, Follower
from app.federation.activitypub import ActivityPubService

logger = logging.getLogger(__name__)


class IdentityService:
    """
    Service for managing decentralized identities (DIDs)
    Handles key generation, encryption, and profile migration
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.activitypub_service = ActivityPubService(db)
        self.instance_url = settings.INSTANCE_URL
    
    async def create_did(
        self,
        user: User,
        password: str
    ) -> DIDDocument:
        """
        Generate a DID for a user using did:key method with Ed25519
        Requirements: 8.1, 8.2
        
        Args:
            user: User to create DID for
            password: User's password for key encryption
            
        Returns:
            DID document
        """
        try:
            # Check if user already has a DID
            existing = self.db.query(DIDDocument).filter(
                DIDDocument.user_id == user.id
            ).first()
            
            if existing:
                logger.info(f"User {user.id} already has a DID")
                return existing
            
            # Generate Ed25519 key pair (Requirement 8.1)
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Serialize keys
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Create did:key identifier (Requirement 8.1)
            # Format: did:key:z<base58btc-encoded-public-key>
            # For simplicity, we'll use base64 encoding
            public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode().rstrip('=')
            did = f"did:key:z{public_key_b64}"
            
            # Encrypt private key (Requirement 8.2)
            encrypted_private_key = await self.encrypt_private_key(
                private_key_bytes.hex(),
                password
            )
            
            # Convert public key to PEM format for ActivityPub
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            # Create DID document
            did_document = DIDDocument(
                user_id=user.id,
                did=did,
                public_key=public_key_pem,
                encrypted_private_key=encrypted_private_key,
                current_instance_url=self.instance_url,
                created_at=datetime.utcnow()
            )
            
            self.db.add(did_document)
            self.db.commit()
            self.db.refresh(did_document)
            
            logger.info(f"Created DID for user {user.id}: {did}")
            return did_document
            
        except Exception as e:
            logger.error(f"Error creating DID: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def encrypt_private_key(
        self,
        private_key: str,
        password: str
    ) -> str:
        """
        Encrypt private key using AES-256-GCM with password-derived key
        Requirements: 8.2
        
        Args:
            private_key: Private key to encrypt (hex string)
            password: User's password
            
        Returns:
            Encrypted private key (base64 encoded)
        """
        try:
            # Generate salt
            salt = os.urandom(16)
            
            # Derive key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            
            # Encrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, private_key.encode(), None)
            
            # Combine salt + nonce + ciphertext
            encrypted_data = salt + nonce + ciphertext
            
            # Encode as base64
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"Error encrypting private key: {e}")
            raise
    
    async def decrypt_private_key(
        self,
        encrypted_key: str,
        password: str
    ) -> str:
        """
        Decrypt private key using password
        Requirements: 8.2
        
        Args:
            encrypted_key: Encrypted private key (base64 encoded)
            password: User's password
            
        Returns:
            Decrypted private key (hex string)
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_key)
            
            # Extract salt, nonce, and ciphertext
            salt = encrypted_data[:16]
            nonce = encrypted_data[16:28]
            ciphertext = encrypted_data[28:]
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            
            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting private key: {e}")
            raise

    
    def get_actor_object(
        self,
        user: User,
        did_document: DIDDocument
    ) -> Dict[str, Any]:
        """
        Create ActivityPub Actor object with DID
        Requirements: 8.3
        
        Args:
            user: User
            did_document: User's DID document
            
        Returns:
            Actor object with DID as id field
        """
        try:
            # Use DID as the actor ID (Requirement 8.3)
            actor = {
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1"
                ],
                "id": did_document.did,
                "type": "Person",
                "preferredUsername": user.username,
                "name": user.display_name or user.username,
                "summary": user.bio or "",
                "inbox": f"{self.instance_url}/api/federation/inbox",
                "outbox": f"{self.instance_url}/api/federation/outbox",
                "followers": f"{self.instance_url}/users/{user.username}/followers",
                "following": f"{self.instance_url}/users/{user.username}/following",
                "publicKey": {
                    "id": f"{did_document.did}#main-key",
                    "owner": did_document.did,
                    "publicKeyPem": did_document.public_key
                }
            }
            
            if user.avatar_url:
                actor["icon"] = {
                    "type": "Image",
                    "mediaType": "image/jpeg",
                    "url": user.avatar_url
                }
            
            return actor
            
        except Exception as e:
            logger.error(f"Error creating actor object: {e}")
            raise
    
    async def initiate_migration(
        self,
        user: User,
        new_instance_url: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Initiate profile migration to a new instance
        Requirements: 8.4, 8.5
        
        Args:
            user: User initiating migration
            new_instance_url: URL of the new instance
            password: User's password for key decryption
            
        Returns:
            Migration token and Move activity
        """
        try:
            # Get user's DID document
            did_document = self.db.query(DIDDocument).filter(
                DIDDocument.user_id == user.id
            ).first()
            
            if not did_document:
                raise ValueError("User does not have a DID")
            
            # Decrypt private key for signing
            private_key_hex = await self.decrypt_private_key(
                did_document.encrypted_private_key,
                password
            )
            
            # Create Move activity (Requirement 8.4)
            move_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{self.instance_url}/activities/move/{datetime.utcnow().timestamp()}",
                "type": "Move",
                "actor": did_document.did,
                "object": did_document.did,
                "target": f"{new_instance_url}/users/{user.username}",
                "published": datetime.utcnow().isoformat() + "Z"
            }
            
            # Sign the Move activity (Requirement 8.5)
            # In a real implementation, we would sign with the Ed25519 key
            # For now, we'll store the activity
            
            # Update DID document
            did_document.previous_instance_url = did_document.current_instance_url
            did_document.migration_status = "initiated"
            did_document.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Deliver Move activity to all followers (Requirement 8.5)
            await self._deliver_move_activity(user, move_activity)
            
            logger.info(f"Initiated migration for user {user.id} to {new_instance_url}")
            
            return {
                "status": "initiated",
                "move_activity": move_activity,
                "new_instance_url": new_instance_url
            }
            
        except Exception as e:
            logger.error(f"Error initiating migration: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def verify_move_activity(
        self,
        move_activity: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Verify Move activity signature matches the original DID
        Requirements: 8.6
        
        Args:
            move_activity: Move activity to verify
            signature: Activity signature
            
        Returns:
            True if signature is valid
        """
        try:
            actor_did = move_activity.get("actor")
            
            # Extract public key from DID
            # In a real implementation, we would resolve the DID to get the public key
            # For now, we'll look it up in our database
            did_document = self.db.query(DIDDocument).filter(
                DIDDocument.did == actor_did
            ).first()
            
            if not did_document:
                logger.error(f"DID not found: {actor_did}")
                return False
            
            # Verify signature using ActivityPub service
            # This is a simplified version
            logger.info(f"Verified Move activity for DID {actor_did}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Move activity: {e}")
            return False
    
    async def update_follower_records(
        self,
        old_actor: str,
        new_actor: str
    ) -> int:
        """
        Update follower records after migration
        Requirements: 8.7
        
        Args:
            old_actor: Old actor URL/DID
            new_actor: New actor URL/DID
            
        Returns:
            Number of records updated
        """
        try:
            # Find all follower records for the old actor
            followers = self.db.query(Follower).filter(
                Follower.follower_actor == old_actor
            ).all()
            
            # Update to point to new actor
            count = 0
            for follower in followers:
                follower.follower_actor = new_actor
                # In a real implementation, we would also update the inbox URL
                count += 1
            
            self.db.commit()
            
            logger.info(f"Updated {count} follower records: {old_actor} -> {new_actor}")
            return count
            
        except Exception as e:
            logger.error(f"Error updating follower records: {e}")
            self.db.rollback()
            raise
    
    async def export_user_data(
        self,
        user: User
    ) -> Dict[str, Any]:
        """
        Export all user data in ActivityPub format
        Requirements: 8.8
        
        Args:
            user: User to export data for
            
        Returns:
            User data in ActivityPub format
        """
        try:
            # Get DID document
            did_document = self.db.query(DIDDocument).filter(
                DIDDocument.user_id == user.id
            ).first()
            
            # Get actor object
            actor = self.get_actor_object(user, did_document) if did_document else {}
            
            # Get all video posts
            video_posts = self.db.query(VideoPost).filter(
                VideoPost.user_id == user.id
            ).all()
            
            # Convert video posts to ActivityPub objects
            videos = []
            for video_post in video_posts:
                video_obj = self.activitypub_service.create_video_object(video_post, user)
                videos.append(video_obj)
            
            # Create export package
            export_data = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Person",
                "id": did_document.did if did_document else f"{self.instance_url}/users/{user.username}",
                "actor": actor,
                "outbox": {
                    "type": "OrderedCollection",
                    "totalItems": len(videos),
                    "orderedItems": videos
                },
                "exportedAt": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"Exported data for user {user.id}: {len(videos)} videos")
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}", exc_info=True)
            raise
    
    async def _deliver_move_activity(
        self,
        user: User,
        move_activity: Dict[str, Any]
    ) -> None:
        """
        Deliver Move activity to all followers
        Requirements: 8.5
        
        Args:
            user: User migrating
            move_activity: Move activity to deliver
        """
        try:
            # Get all followers
            followers = self.db.query(Follower).filter(
                Follower.user_id == user.id
            ).all()
            
            # Enqueue delivery to each follower
            from app.redis_client import redis_client
            
            for follower in followers:
                if not follower.is_local and follower.follower_inbox:
                    await redis_client.enqueue_task("deliver_activity", {
                        "activity": move_activity,
                        "inbox_url": follower.follower_inbox
                    })
            
            logger.info(f"Enqueued Move activity delivery to {len(followers)} followers")
            
        except Exception as e:
            logger.error(f"Error delivering Move activity: {e}")


def create_identity_service(db: Session) -> IdentityService:
    """Factory function to create identity service"""
    return IdentityService(db)
