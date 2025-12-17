"""
Upload Manager Service
Handles video file uploads, validation, and session management
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any
from pathlib import Path
import subprocess
import json

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
import redis

from app.config import settings
from app.models import VideoPost
from app.schemas import VideoMetadata, ValidationResult, UploadSessionResponse


class UploadSession:
    """Represents an upload session for chunked uploads"""
    
    def __init__(
        self,
        session_id: str,
        user_id: int,
        filename: str,
        file_size: int,
        total_chunks: int,
        temp_file_path: str,
        created_at: datetime,
        expires_at: datetime
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.filename = filename
        self.file_size = file_size
        self.total_chunks = total_chunks
        self.uploaded_chunks: Set[int] = set()
        self.temp_file_path = temp_file_path
        self.created_at = created_at
        self.expires_at = expires_at
        self.status = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for Redis storage"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "total_chunks": self.total_chunks,
            "uploaded_chunks": list(self.uploaded_chunks),
            "temp_file_path": self.temp_file_path,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadSession":
        """Create session from dictionary"""
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            filename=data["filename"],
            file_size=data["file_size"],
            total_chunks=data["total_chunks"],
            temp_file_path=data["temp_file_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
        )
        session.uploaded_chunks = set(data.get("uploaded_chunks", []))
        session.status = data.get("status", "active")
        return session


class UploadManager:
    """Manages video file uploads and validation"""
    
    def __init__(self, redis_client: redis.Redis, db: Session):
        self.redis_client = redis_client
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_video_format(self, filename: str) -> ValidationResult:
        """
        Validate video file format against supported codecs
        Requirements: 1.1
        """
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext not in settings.SUPPORTED_VIDEO_FORMATS:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unsupported format: {file_ext}. Supported formats: {', '.join(settings.SUPPORTED_VIDEO_FORMATS)}"]
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_file_size(self, file_size: int) -> ValidationResult:
        """
        Validate file size against maximum limit
        Requirements: 1.2
        """
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        
        if file_size > max_size_bytes:
            return ValidationResult(
                is_valid=False,
                errors=[f"File size {file_size / 1024 / 1024:.2f}MB exceeds maximum {settings.MAX_UPLOAD_SIZE_MB}MB"]
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_video_duration(self, file_path: str) -> ValidationResult:
        """
        Validate video duration using ffprobe
        Requirements: 1.3
        """
        try:
            # Use ffprobe to get video duration
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return ValidationResult(
                    is_valid=False,
                    errors=["Could not determine video duration"]
                )
            
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            
            if duration > settings.MAX_VIDEO_DURATION_SEC:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Video duration {duration:.1f}s exceeds maximum {settings.MAX_VIDEO_DURATION_SEC}s"]
                )
            
            return ValidationResult(is_valid=True)
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                is_valid=False,
                errors=["Video duration check timed out"]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error checking video duration: {str(e)}"]
            )
    
    def validate_metadata(self, metadata: VideoMetadata) -> ValidationResult:
        """
        Validate video metadata constraints
        Requirements: 1.7
        """
        errors = []
        
        # Validate title length
        if len(metadata.title) > 200:
            errors.append(f"Title exceeds 200 characters (current: {len(metadata.title)})")
        
        # Validate description length
        if metadata.description and len(metadata.description) > 2000:
            errors.append(f"Description exceeds 2000 characters (current: {len(metadata.description)})")
        
        # Validate tags count
        if len(metadata.tags) > 10:
            errors.append(f"Too many tags (maximum: 10, current: {len(metadata.tags)})")
        
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        
        return ValidationResult(is_valid=True)
    
    async def initiate_upload(
        self,
        user_id: int,
        filename: str,
        file_size: int,
        total_chunks: int = 1
    ) -> UploadSession:
        """
        Initiate a new upload session
        Requirements: 1.4
        """
        # Validate format and size
        format_validation = self.validate_video_format(filename)
        if not format_validation.is_valid:
            raise HTTPException(status_code=400, detail=format_validation.errors[0])
        
        size_validation = self.validate_file_size(file_size)
        if not size_validation.is_valid:
            raise HTTPException(status_code=413, detail=size_validation.errors[0])
        
        # Create session
        session_id = str(uuid.uuid4())
        temp_file_path = str(self.upload_dir / f"temp_{session_id}_{filename}")
        
        session = UploadSession(
            session_id=session_id,
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            total_chunks=total_chunks,
            temp_file_path=temp_file_path,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Store session in Redis
        self.redis_client.setex(
            f"upload_session:{session_id}",
            86400,  # 24 hours
            json.dumps(session.to_dict())
        )
        
        return session
    
    async def upload_chunk(
        self,
        session_id: str,
        chunk_number: int,
        chunk_data: bytes
    ) -> Dict[str, Any]:
        """
        Upload a chunk of video data
        Requirements: 1.5
        """
        # Retrieve session
        session_data = self.redis_client.get(f"upload_session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Upload session not found or expired")
        
        session = UploadSession.from_dict(json.loads(session_data))
        
        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            session.status = "expired"
            raise HTTPException(status_code=410, detail="Upload session expired")
        
        # Validate chunk number
        if chunk_number < 0 or chunk_number >= session.total_chunks:
            raise HTTPException(status_code=400, detail="Invalid chunk number")
        
        # Write chunk to file
        mode = 'ab' if chunk_number > 0 else 'wb'
        with open(session.temp_file_path, mode) as f:
            f.write(chunk_data)
        
        # Update session
        session.uploaded_chunks.add(chunk_number)
        
        # Save updated session
        self.redis_client.setex(
            f"upload_session:{session_id}",
            86400,
            json.dumps(session.to_dict())
        )
        
        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "uploaded_chunks": len(session.uploaded_chunks),
            "total_chunks": session.total_chunks,
            "complete": len(session.uploaded_chunks) == session.total_chunks
        }
    
    def compute_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def finalize_upload(
        self,
        session_id: str,
        metadata: VideoMetadata,
        expected_checksum: Optional[str] = None
    ) -> VideoPost:
        """
        Finalize upload and create Video Post record
        Requirements: 1.6, 1.7, 1.8
        """
        # Retrieve session
        session_data = self.redis_client.get(f"upload_session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        session = UploadSession.from_dict(json.loads(session_data))
        
        # Verify all chunks uploaded
        if len(session.uploaded_chunks) != session.total_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Incomplete upload: {len(session.uploaded_chunks)}/{session.total_chunks} chunks"
            )
        
        # Validate checksum if provided
        if expected_checksum:
            actual_checksum = self.compute_checksum(session.temp_file_path)
            if actual_checksum != expected_checksum:
                raise HTTPException(status_code=400, detail="Checksum mismatch")
        
        # Validate duration
        duration_validation = self.validate_video_duration(session.temp_file_path)
        if not duration_validation.is_valid:
            # Clean up temp file
            if os.path.exists(session.temp_file_path):
                os.remove(session.temp_file_path)
            raise HTTPException(status_code=400, detail=duration_validation.errors[0])
        
        # Validate metadata
        metadata_validation = self.validate_metadata(metadata)
        if not metadata_validation.is_valid:
            # Clean up temp file
            if os.path.exists(session.temp_file_path):
                os.remove(session.temp_file_path)
            raise HTTPException(status_code=400, detail=metadata_validation.errors[0])
        
        # Move file to permanent location
        final_filename = f"{uuid.uuid4()}_{session.filename}"
        final_path = str(self.upload_dir / final_filename)
        os.rename(session.temp_file_path, final_path)
        
        # Get video duration for database
        cmd = [
            settings.FFPROBE_PATH,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            final_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        duration = int(float(data.get('format', {}).get('duration', 0)))
        
        # Create Video Post record
        video_post = VideoPost(
            user_id=session.user_id,
            title=metadata.title,
            description=metadata.description,
            tags=metadata.tags,
            duration=duration,
            status="processing",
            original_file_path=final_path,
            created_at=datetime.utcnow()
        )
        
        self.db.add(video_post)
        self.db.commit()
        self.db.refresh(video_post)
        
        # Enqueue transcoding task (Requirements: 2.1)
        # In production, this would push to Redis queue for Celery/RQ worker
        # For now, we store the task info in Redis for manual processing
        task_data = {
            "video_post_id": video_post.id,
            "input_path": final_path,
            "created_at": datetime.utcnow().isoformat()
        }
        self.redis_client.lpush("video_processing_queue", json.dumps(task_data))
        
        # Clean up session
        self.redis_client.delete(f"upload_session:{session_id}")
        session.status = "completed"
        
        return video_post
    
    async def validate_video_file(self, file_path: str) -> ValidationResult:
        """
        Comprehensive video file validation
        """
        errors = []
        warnings = []
        
        # Check file exists
        if not os.path.exists(file_path):
            return ValidationResult(is_valid=False, errors=["File not found"])
        
        # Check file size
        file_size = os.path.getsize(file_path)
        size_validation = self.validate_file_size(file_size)
        if not size_validation.is_valid:
            errors.extend(size_validation.errors)
        
        # Check duration
        duration_validation = self.validate_video_duration(file_path)
        if not duration_validation.is_valid:
            errors.extend(duration_validation.errors)
        
        # Check video codec
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'json',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            codec = data.get('streams', [{}])[0].get('codec_name', '')
            
            if codec and codec not in ['h264', 'vp8', 'vp9']:
                warnings.append(f"Video codec {codec} may require transcoding")
        except Exception:
            warnings.append("Could not determine video codec")
        
        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        return ValidationResult(is_valid=True, warnings=warnings)
