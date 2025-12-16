"""
Media Worker
Handles video transcoding and thumbnail generation
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from app.config import settings
from app.models import VideoPost
from app.schemas import TranscodeResult

logger = logging.getLogger(__name__)


class ThumbnailInfo:
    """Information about a generated thumbnail"""
    
    def __init__(self, size: str, path: str, width: int, height: int):
        self.size = size
        self.path = path
        self.width = width
        self.height = height


class VideoProcessingTask:
    """Represents a video processing task"""
    
    def __init__(self, video_post_id: int, input_path: str):
        self.video_post_id = video_post_id
        self.input_path = input_path
        self.created_at = datetime.utcnow()


class ProcessingResult:
    """Result of video processing"""
    
    def __init__(
        self,
        success: bool,
        video_post_id: int,
        resolutions: Optional[Dict[str, str]] = None,
        thumbnails: Optional[Dict[str, str]] = None,
        duration: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.video_post_id = video_post_id
        self.resolutions = resolutions or {}
        self.thumbnails = thumbnails or {}
        self.duration = duration
        self.error = error


class MediaWorker:
    """Handles video transcoding and thumbnail generation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.processed_dir = Path(settings.PROCESSED_DIR)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create resolution directories
        for resolution in settings.TRANSCODE_RESOLUTIONS:
            (self.processed_dir / resolution).mkdir(parents=True, exist_ok=True)
        
        # Create thumbnails directory
        (self.processed_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
    
    def get_video_info(self, input_path: str) -> Dict:
        """
        Get video information using ffprobe
        """
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'error',
                '-show_entries', 'format=duration:stream=width,height,codec_name',
                '-of', 'json',
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return {}
            
            return json.loads(result.stdout)
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def transcode_video(
        self,
        video_post_id: int,
        input_path: str
    ) -> TranscodeResult:
        """
        Transcode video to multiple resolutions
        Requirements: 2.2, 2.3, 2.4
        """
        try:
            # Get video info
            video_info = self.get_video_info(input_path)
            if not video_info:
                return TranscodeResult(
                    success=False,
                    resolutions={},
                    thumbnails={},
                    duration=0,
                    error="Could not get video information"
                )
            
            duration = int(float(video_info.get('format', {}).get('duration', 0)))
            
            # Get original dimensions
            streams = video_info.get('streams', [])
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
            original_width = video_stream.get('width', 1920)
            original_height = video_stream.get('height', 1080)
            
            resolutions = {}
            resolution_map = {
                '360p': (640, 360),
                '480p': (854, 480),
                '720p': (1280, 720),
                '1080p': (1920, 1080)
            }
            
            # Transcode to each resolution
            for resolution_name in settings.TRANSCODE_RESOLUTIONS:
                target_width, target_height = resolution_map[resolution_name]
                
                # Skip if original is smaller than target
                if original_height < target_height:
                    logger.info(f"Skipping {resolution_name} - original is smaller")
                    continue
                
                output_filename = f"{video_post_id}_{resolution_name}.mp4"
                output_path = str(self.processed_dir / resolution_name / output_filename)
                
                # FFmpeg command for transcoding with H.264
                cmd = [
                    settings.FFMPEG_PATH,
                    '-i', input_path,
                    '-c:v', 'libx264',  # H.264 codec
                    '-preset', 'medium',
                    '-crf', '23',
                    '-vf', f'scale={target_width}:{target_height}',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',  # Overwrite output file
                    output_path
                ]
                
                logger.info(f"Transcoding to {resolution_name}...")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode != 0:
                    logger.error(f"Transcoding to {resolution_name} failed: {result.stderr}")
                    continue
                
                resolutions[resolution_name] = output_path
                logger.info(f"✓ Transcoded to {resolution_name}")
            
            if not resolutions:
                return TranscodeResult(
                    success=False,
                    resolutions={},
                    thumbnails={},
                    duration=duration,
                    error="Failed to transcode to any resolution"
                )
            
            return TranscodeResult(
                success=True,
                resolutions=resolutions,
                thumbnails={},
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            logger.error("Transcoding timed out")
            return TranscodeResult(
                success=False,
                resolutions={},
                thumbnails={},
                duration=0,
                error="Transcoding timed out"
            )
        except Exception as e:
            logger.error(f"Transcoding error: {e}")
            return TranscodeResult(
                success=False,
                resolutions={},
                thumbnails={},
                duration=0,
                error=str(e)
            )
    
    def generate_thumbnails(
        self,
        video_path: str,
        output_dir: str
    ) -> List[ThumbnailInfo]:
        """
        Generate thumbnail images at multiple sizes
        Requirements: 2.5, 2.6
        """
        thumbnails = []
        
        try:
            # Extract frame at specified timestamp
            timestamp = settings.THUMBNAIL_TIMESTAMP_SEC
            
            for size_name, (width, height) in settings.THUMBNAIL_SIZES.items():
                output_filename = f"{Path(video_path).stem}_{size_name}.jpg"
                output_path = os.path.join(output_dir, output_filename)
                
                cmd = [
                    settings.FFMPEG_PATH,
                    '-ss', str(timestamp),
                    '-i', video_path,
                    '-vframes', '1',
                    '-vf', f'scale={width}:{height}',
                    '-q:v', '2',  # High quality
                    '-y',
                    output_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    thumbnails.append(ThumbnailInfo(
                        size=size_name,
                        path=output_path,
                        width=width,
                        height=height
                    ))
                    logger.info(f"✓ Generated {size_name} thumbnail")
                else:
                    logger.error(f"Failed to generate {size_name} thumbnail: {result.stderr}")
            
            return thumbnails
            
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")
            return thumbnails
    
    async def process_video_task(
        self,
        task: VideoProcessingTask
    ) -> ProcessingResult:
        """
        Process a video task: transcode and generate thumbnails
        Requirements: 2.1, 2.7, 2.8
        """
        video_post_id = task.video_post_id
        input_path = task.input_path
        
        logger.info(f"Processing video {video_post_id}...")
        
        try:
            # Get video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.id == video_post_id
            ).first()
            
            if not video_post:
                logger.error(f"Video post {video_post_id} not found")
                return ProcessingResult(
                    success=False,
                    video_post_id=video_post_id,
                    error="Video post not found"
                )
            
            # Update status to processing
            video_post.status = "processing"
            self.db.commit()
            
            # Transcode video
            transcode_result = self.transcode_video(video_post_id, input_path)
            
            if not transcode_result.success:
                # Mark as failed
                video_post.status = "failed"
                video_post.error_message = transcode_result.error
                self.db.commit()
                
                logger.error(f"Video {video_post_id} processing failed: {transcode_result.error}")
                return ProcessingResult(
                    success=False,
                    video_post_id=video_post_id,
                    error=transcode_result.error
                )
            
            # Generate thumbnails from the highest quality version
            thumbnail_dir = str(self.processed_dir / "thumbnails")
            thumbnails_info = self.generate_thumbnails(input_path, thumbnail_dir)
            
            # Build thumbnails dict
            thumbnails = {}
            for thumb in thumbnails_info:
                thumbnails[thumb.size] = thumb.path
            
            # Update video post with results
            video_post.resolutions = transcode_result.resolutions
            video_post.duration = transcode_result.duration
            
            if 'small' in thumbnails:
                video_post.thumbnail_small = thumbnails['small']
            if 'medium' in thumbnails:
                video_post.thumbnail_medium = thumbnails['medium']
            if 'large' in thumbnails:
                video_post.thumbnail_large = thumbnails['large']
            
            # Mark as ready
            video_post.status = "ready"
            video_post.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"✓ Video {video_post_id} processed successfully")
            
            # Enqueue embedding generation task (Requirement 3.1)
            try:
                self.enqueue_embedding_task(video_post_id)
            except Exception as e:
                logger.error(f"Failed to enqueue embedding task for video {video_post_id}: {e}")
            
            return ProcessingResult(
                success=True,
                video_post_id=video_post_id,
                resolutions=transcode_result.resolutions,
                thumbnails=thumbnails,
                duration=transcode_result.duration
            )
            
        except Exception as e:
            logger.error(f"Error processing video {video_post_id}: {e}")
            
            # Mark as failed
            try:
                video_post = self.db.query(VideoPost).filter(
                    VideoPost.id == video_post_id
                ).first()
                if video_post:
                    video_post.status = "failed"
                    video_post.error_message = str(e)
                    self.db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update video post status: {db_error}")
            
            return ProcessingResult(
                success=False,
                video_post_id=video_post_id,
                error=str(e)
            )
    
    def enqueue_processing_task(self, video_post_id: int, input_path: str):
        """
        Enqueue a video processing task
        Requirements: 2.1
        
        Note: In a production system, this would add the task to a queue (Redis/Celery)
        For now, we'll process synchronously
        """
        task = VideoProcessingTask(video_post_id, input_path)
        logger.info(f"Enqueued processing task for video {video_post_id}")
        return task
    
    def enqueue_embedding_task(self, video_post_id: int):
        """
        Enqueue an embedding generation task when video becomes ready
        Requirements: 3.1
        
        Note: In a production system, this would add the task to a queue (Redis/Celery)
        For now, we'll use a simple Redis list as a queue
        """
        from app.redis_client import get_sync_redis
        
        try:
            redis_client = get_sync_redis()
            task_data = json.dumps({
                'video_post_id': video_post_id,
                'task_type': 'embedding',
                'created_at': datetime.utcnow().isoformat()
            })
            redis_client.lpush(settings.TASK_QUEUE_NAME, task_data)
            logger.info(f"✓ Enqueued embedding task for video {video_post_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue embedding task: {e}")
            raise


def create_media_worker(db: Session) -> MediaWorker:
    """Factory function to create media worker"""
    return MediaWorker(db)
