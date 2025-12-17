"""
Qdrant vector database client for storing and querying video embeddings
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional, Dict, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manager for Qdrant vector database operations"""
    
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = settings.QDRANT_COLLECTION_NAME
    
    def connect(self):
        """Initialize Qdrant client and create collection if needed"""
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            
            # Check if collection exists, create if not
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def disconnect(self):
        """Close Qdrant connection"""
        if self.client:
            self.client.close()
            logger.info("Qdrant connection closed")
    
    def upsert_embedding(
        self,
        video_post_id: int,
        embedding: List[float],
        payload: Dict[str, Any]
    ):
        """
        Store or update video embedding in Qdrant
        
        Args:
            video_post_id: Unique identifier for the video post
            embedding: 512-dimensional embedding vector
            payload: Metadata (user_id, created_at, tags, engagement_score, etc.)
        """
        try:
            point = PointStruct(
                id=video_post_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.info(f"Upserted embedding for video post {video_post_id}")
            
        except Exception as e:
            logger.error(f"Failed to upsert embedding for video {video_post_id}: {e}")
            raise
    
    def search_similar(
        self,
        query_vector: List[float],
        limit: int = 100,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar videos using cosine similarity
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filters on metadata
            
        Returns:
            List of results with id, score, and payload
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions
            )
            
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search similar videos: {e}")
            raise
    
    def get_embedding(self, video_post_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve embedding and metadata for a specific video
        
        Args:
            video_post_id: Video post identifier
            
        Returns:
            Dictionary with vector and payload, or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[video_post_id]
            )
            
            if result:
                point = result[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve embedding for video {video_post_id}: {e}")
            return None
    
    def delete_embedding(self, video_post_id: int):
        """
        Delete embedding for a video post
        
        Args:
            video_post_id: Video post identifier
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[video_post_id]
            )
            logger.info(f"Deleted embedding for video post {video_post_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete embedding for video {video_post_id}: {e}")
            raise
    
    def count_vectors(self) -> int:
        """Get total number of vectors in collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            return 0


# Global Qdrant manager instance
qdrant_manager = QdrantManager()


def get_qdrant() -> QdrantManager:
    """Dependency for getting Qdrant manager"""
    return qdrant_manager
