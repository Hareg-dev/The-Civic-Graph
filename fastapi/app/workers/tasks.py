"""
Celery tasks for background processing
"""

from celery import Celery
from app.config import settings
from app.db import SessionLocal
from app.workers.media import MediaWorker
from app.ai.embeddings import EmbeddingService
from app.ai.qdrant_client import QdrantManager
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'freewill_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
)


@celery_app.task(name='process_video', bind=True, max_retries=3)
def process_video_task(self, video_post_id: int, input_path: str):
    """
    Process video: transcode and generate thumbnails
    
    Args:
        video_post_id: ID of the video post
        input_path: Path to the uploaded video file
    """
    logger.info(f"Starting video processing for post {video_post_id}")
    
    db = SessionLocal()
    try:
        worker = MediaWorker(db)
        result = worker.process_video(video_post_id, input_path)
        
        if result.success:
            logger.info(f"Video processing completed for post {video_post_id}")
            # Trigger embedding generation
            generate_embedding_task.delay(video_post_id)
        else:
            logger.error(f"Video processing failed for post {video_post_id}: {result.error}")
            raise Exception(result.error)
        
        return {"success": True, "video_post_id": video_post_id}
    
    except Exception as e:
        logger.error(f"Error processing video {video_post_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(name='generate_embedding', bind=True, max_retries=3)
def generate_embedding_task(self, video_post_id: int):
    """
    Generate embeddings for a video
    
    Args:
        video_post_id: ID of the video post
    """
    logger.info(f"Starting embedding generation for post {video_post_id}")
    
    db = SessionLocal()
    try:
        qdrant = QdrantManager()
        embedding_service = EmbeddingService(db, qdrant)
        
        # Process embedding (async function, run in sync context)
        import asyncio
        success = asyncio.run(
            embedding_service.process_video_embedding(video_post_id)
        )
        
        if success:
            logger.info(f"Embedding generation completed for post {video_post_id}")
        else:
            logger.error(f"Embedding generation failed for post {video_post_id}")
            raise Exception("Embedding generation failed")
        
        return {"success": True, "video_post_id": video_post_id}
    
    except Exception as e:
        logger.error(f"Error generating embedding for video {video_post_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(name='deliver_activity')
def deliver_activity_task(activity_id: int, inbox_url: str):
    """
    Deliver ActivityPub activity to remote inbox
    
    Args:
        activity_id: ID of the activity to deliver
        inbox_url: URL of the remote inbox
    """
    logger.info(f"Delivering activity {activity_id} to {inbox_url}")
    
    from app.federation.outbox import OutboxHandler
    from app.db import SessionLocal
    
    db = SessionLocal()
    try:
        handler = OutboxHandler(db)
        import asyncio
        success = asyncio.run(
            handler.deliver_to_inbox(activity_id, inbox_url)
        )
        
        if success:
            logger.info(f"Activity {activity_id} delivered to {inbox_url}")
        else:
            logger.error(f"Failed to deliver activity {activity_id} to {inbox_url}")
        
        return {"success": success, "activity_id": activity_id, "inbox_url": inbox_url}
    
    except Exception as e:
        logger.error(f"Error delivering activity {activity_id}: {e}")
        raise
    
    finally:
        db.close()
