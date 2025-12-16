"""
Embedding Worker
Processes embedding generation tasks from the queue
Requirements: 3.1-3.8
"""

import json
import logging
import time
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from app.config import settings
from app.redis_client import get_sync_redis
from app.ai.embeddings import EmbeddingService
from app.ai.qdrant_client import QdrantManager
from app.db import SessionLocal

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """
    Background worker that processes embedding generation tasks
    """
    
    def __init__(self):
        self.redis_client = get_sync_redis()
        self.queue_name = settings.TASK_QUEUE_NAME
        self.running = False
    
    def process_task(self, task_data: dict) -> bool:
        """
        Process a single embedding task
        
        Args:
            task_data: Task data containing video_post_id
            
        Returns:
            True if successful, False otherwise
        """
        video_post_id = task_data.get('video_post_id')
        
        if not video_post_id:
            logger.error("Task missing video_post_id")
            return False
        
        logger.info(f"Processing embedding task for video {video_post_id}")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Create services
            qdrant = QdrantManager()
            embedding_service = EmbeddingService(db, qdrant)
            
            # Process the video embedding
            import asyncio
            success = asyncio.run(
                embedding_service.process_video_embedding(video_post_id)
            )
            
            if success:
                logger.info(f"✓ Successfully processed embedding for video {video_post_id}")
            else:
                logger.error(f"Failed to process embedding for video {video_post_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing embedding task for video {video_post_id}: {e}")
            return False
        finally:
            db.close()
    
    def run(self, poll_interval: int = 1):
        """
        Run the worker loop
        
        Args:
            poll_interval: Seconds to wait between queue checks
        """
        self.running = True
        logger.info(f"Embedding worker started, polling queue '{self.queue_name}'")
        
        while self.running:
            try:
                # Pop task from queue (blocking with timeout)
                task_json = self.redis_client.brpop(self.queue_name, timeout=poll_interval)
                
                if task_json:
                    # brpop returns (key, value) tuple
                    _, task_data_str = task_json
                    
                    try:
                        task_data = json.loads(task_data_str)
                        
                        # Only process embedding tasks
                        if task_data.get('task_type') == 'embedding':
                            self.process_task(task_data)
                        else:
                            logger.warning(f"Unknown task type: {task_data.get('task_type')}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode task JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error processing task: {e}")
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping worker...")
                self.running = False
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(poll_interval)
        
        logger.info("Embedding worker stopped")
    
    def stop(self):
        """Stop the worker"""
        self.running = False


def run_embedding_worker():
    """
    Entry point for running the embedding worker
    """
    worker = EmbeddingWorker()
    worker.run()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_embedding_worker()
