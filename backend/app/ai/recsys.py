"""
Recommendation Engine for personalized video feed generation
Combines user preferences, vector similarity, recency, and engagement signals
Requirements: 4.1-4.8
"""

import numpy as np
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.config import settings
from app.models import VideoPost, UserInteraction
from app.schemas import FeedResponse, VideoPostResponse
from app.ai.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    AI-powered recommendation engine for personalized video feeds
    Combines collaborative filtering with content-based recommendations
    """
    
    def __init__(self, db: Session, qdrant: QdrantManager):
        self.db = db
        self.qdrant = qdrant
        
        # Configuration from settings
        self.lookback_days = settings.INTERACTION_LOOKBACK_DAYS
        self.similarity_weight = settings.SIMILARITY_WEIGHT
        self.recency_weight = settings.RECENCY_WEIGHT
        self.engagement_weight = settings.ENGAGEMENT_WEIGHT
        self.page_size = settings.FEED_PAGE_SIZE
        self.trending_window_hours = settings.TRENDING_WINDOW_HOURS
        self.cold_start_threshold = settings.COLD_START_INTERACTION_THRESHOLD
    
    async def generate_feed(
        self,
        user_id: int,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> FeedResponse:
        """
        Generate personalized feed for user
        Requirements: 4.1-4.8
        
        Args:
            user_id: User requesting feed
            limit: Number of videos to return
            cursor: Pagination cursor (base64 encoded offset)
            
        Returns:
            FeedResponse with videos and pagination info
        """
        try:
            logger.info(f"Generating feed for user {user_id}")
            
            # Parse cursor for offset
            offset = self._parse_cursor(cursor)
            
            # Check if user has sufficient interaction history
            interaction_count = self._get_interaction_count(user_id)
            
            if interaction_count < self.cold_start_threshold:
                # Cold start: use trending videos
                logger.info(f"User {user_id} has {interaction_count} interactions, using trending feed")
                videos = await self.get_trending_videos(limit=limit, offset=offset)
            else:
                # Personalized feed
                logger.info(f"User {user_id} has {interaction_count} interactions, using personalized feed")
                videos = await self._generate_personalized_feed(
                    user_id=user_id,
                    limit=limit,
                    offset=offset
                )
            
            # Create pagination cursor
            has_more = len(videos) == limit
            next_cursor = self._create_cursor(offset + len(videos)) if has_more else None
            
            # Convert to response schema
            video_responses = [
                VideoPostResponse.from_orm(video) for video in videos
            ]
            
            logger.info(f"Generated feed with {len(videos)} videos for user {user_id}")
            
            return FeedResponse(
                videos=video_responses,
                next_cursor=next_cursor,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(f"Error generating feed for user {user_id}: {e}")
            # Fallback to trending on error
            videos = await self.get_trending_videos(limit=limit, offset=0)
            video_responses = [VideoPostResponse.from_orm(video) for video in videos]
            return FeedResponse(
                videos=video_responses,
                next_cursor=None,
                has_more=False
            )
    
    async def _generate_personalized_feed(
        self,
        user_id: int,
        limit: int,
        offset: int
    ) -> List[VideoPost]:
        """
        Generate personalized feed using user preferences and vector similarity
        Requirements: 4.1-4.5
        """
        try:
            # Step 1: Compute user preference embedding
            user_embedding = await self.compute_user_embedding(user_id)
            
            if user_embedding is None:
                logger.warning(f"Could not compute user embedding for {user_id}, falling back to trending")
                return await self.get_trending_videos(limit=limit, offset=offset)
            
            # Step 2: Query Qdrant for similar videos
            candidates = await self.query_similar_videos(
                query_embedding=user_embedding,
                limit=100  # Get more candidates for ranking
            )
            
            if not candidates:
                logger.warning(f"No candidates found for user {user_id}, falling back to trending")
                return await self.get_trending_videos(limit=limit, offset=offset)
            
            # Step 3: Rank candidates using combined scoring
            ranked_videos = await self.rank_videos(
                candidates=candidates,
                user_id=user_id
            )
            
            # Step 4: Apply pagination
            paginated = ranked_videos[offset:offset + limit]
            
            return paginated
            
        except Exception as e:
            logger.error(f"Error generating personalized feed: {e}")
            return await self.get_trending_videos(limit=limit, offset=offset)
    
    async def compute_user_embedding(
        self,
        user_id: int,
        lookback_days: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Compute user preference embedding from interaction history
        Requirements: 4.1, 4.2
        
        Args:
            user_id: User ID
            lookback_days: Days to look back (default from settings)
            
        Returns:
            Normalized user preference embedding or None
        """
        try:
            if lookback_days is None:
                lookback_days = self.lookback_days
            
            # Get user interactions from past N days
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            interactions = self.db.query(UserInteraction).filter(
                and_(
                    UserInteraction.user_id == user_id,
                    UserInteraction.created_at >= cutoff_date,
                    UserInteraction.interaction_type.in_(['like', 'view', 'share'])
                )
            ).all()
            
            if not interactions:
                logger.info(f"No interactions found for user {user_id} in past {lookback_days} days")
                return None
            
            # Get embeddings for interacted videos
            video_ids = [interaction.video_post_id for interaction in interactions]
            embeddings = []
            
            for video_id in video_ids:
                embedding_data = self.qdrant.get_embedding(video_id)
                if embedding_data and 'vector' in embedding_data:
                    embeddings.append(np.array(embedding_data['vector']))
            
            if not embeddings:
                logger.warning(f"No embeddings found for user {user_id}'s interactions")
                return None
            
            # Compute average embedding
            avg_embedding = np.mean(embeddings, axis=0)
            
            # Normalize to unit vector
            norm = np.linalg.norm(avg_embedding)
            if norm > 0:
                avg_embedding = avg_embedding / norm
            
            logger.info(f"Computed user embedding for {user_id} from {len(embeddings)} videos")
            
            return avg_embedding
            
        except Exception as e:
            logger.error(f"Error computing user embedding for {user_id}: {e}")
            return None
    
    async def query_similar_videos(
        self,
        query_embedding: np.ndarray,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query Qdrant for similar videos using cosine similarity
        Requirements: 4.3
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            
        Returns:
            List of candidate videos with similarity scores
        """
        try:
            # Query Qdrant
            results = self.qdrant.search_similar(
                query_vector=query_embedding.tolist(),
                limit=limit,
                score_threshold=0.0  # No threshold, we'll rank later
            )
            
            logger.info(f"Found {len(results)} similar videos from Qdrant")
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying similar videos: {e}")
            return []
    
    async def rank_videos(
        self,
        candidates: List[Dict[str, Any]],
        user_id: int
    ) -> List[VideoPost]:
        """
        Rank candidate videos using combined scoring formula
        Requirements: 4.4, 4.5
        
        Formula: 0.6×similarity + 0.25×recency + 0.15×engagement
        
        Args:
            candidates: List of candidates from Qdrant with scores
            user_id: User ID for filtering
            
        Returns:
            Ranked list of VideoPost objects
        """
        try:
            if not candidates:
                return []
            
            # Extract video IDs
            video_ids = [c['id'] for c in candidates]
            
            # Fetch video posts from database
            videos = self.db.query(VideoPost).filter(
                and_(
                    VideoPost.id.in_(video_ids),
                    VideoPost.status == 'ready',
                    VideoPost.moderation_status.in_(['approved', 'pending'])
                )
            ).all()
            
            # Create lookup for similarity scores
            similarity_scores = {c['id']: c['score'] for c in candidates}
            
            # Compute combined scores
            scored_videos = []
            current_time = datetime.utcnow()
            
            for video in videos:
                # Similarity score (already normalized 0-1 from cosine similarity)
                similarity = similarity_scores.get(video.id, 0.0)
                
                # Recency score (exponential decay)
                recency = self._compute_recency_score(video.created_at, current_time)
                
                # Engagement score (normalized)
                engagement = video.engagement_score
                
                # Combined score
                final_score = (
                    self.similarity_weight * similarity +
                    self.recency_weight * recency +
                    self.engagement_weight * engagement
                )
                
                scored_videos.append((video, final_score))
            
            # Sort by final score descending
            scored_videos.sort(key=lambda x: x[1], reverse=True)
            
            # Return just the videos
            ranked = [video for video, score in scored_videos]
            
            logger.info(f"Ranked {len(ranked)} videos for user {user_id}")
            
            return ranked
            
        except Exception as e:
            logger.error(f"Error ranking videos: {e}")
            return []
    
    def _compute_recency_score(
        self,
        created_at: datetime,
        current_time: datetime
    ) -> float:
        """
        Compute recency score with exponential decay
        Requirements: 4.4
        
        Args:
            created_at: Video creation timestamp
            current_time: Current timestamp
            
        Returns:
            Recency score between 0 and 1
        """
        # Age in hours
        age_hours = (current_time - created_at).total_seconds() / 3600
        
        # Exponential decay with half-life of 24 hours
        # Score = 0.5^(age_hours / 24)
        half_life_hours = 24
        score = 0.5 ** (age_hours / half_life_hours)
        
        return score
    
    async def get_trending_videos(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[VideoPost]:
        """
        Get trending videos based on recent engagement
        Requirements: 4.6
        
        Args:
            limit: Number of videos to return
            offset: Pagination offset
            
        Returns:
            List of trending VideoPost objects
        """
        try:
            # Get videos from past 24 hours with high engagement
            cutoff_time = datetime.utcnow() - timedelta(hours=self.trending_window_hours)
            
            videos = self.db.query(VideoPost).filter(
                and_(
                    VideoPost.created_at >= cutoff_time,
                    VideoPost.status == 'ready',
                    VideoPost.moderation_status.in_(['approved', 'pending'])
                )
            ).order_by(
                desc(VideoPost.engagement_score),
                desc(VideoPost.created_at)
            ).offset(offset).limit(limit).all()
            
            logger.info(f"Retrieved {len(videos)} trending videos")
            
            return videos
            
        except Exception as e:
            logger.error(f"Error getting trending videos: {e}")
            return []
    
    async def record_interaction(
        self,
        user_id: int,
        video_post_id: int,
        interaction_type: str
    ) -> bool:
        """
        Record user interaction and trigger async embedding update
        Requirements: 4.8
        
        Args:
            user_id: User ID
            video_post_id: Video post ID
            interaction_type: Type of interaction (view, like, share, comment)
            
        Returns:
            True if successful
        """
        try:
            # Create interaction record
            interaction = UserInteraction(
                user_id=user_id,
                video_post_id=video_post_id,
                interaction_type=interaction_type,
                created_at=datetime.utcnow()
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Recorded {interaction_type} interaction for user {user_id} on video {video_post_id}")
            
            # TODO: Trigger async user embedding update
            # This would be done via a background task/worker
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
            self.db.rollback()
            return False
    
    def _get_interaction_count(self, user_id: int) -> int:
        """Get total interaction count for user"""
        try:
            count = self.db.query(func.count(UserInteraction.id)).filter(
                UserInteraction.user_id == user_id
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Error getting interaction count: {e}")
            return 0
    
    def _parse_cursor(self, cursor: Optional[str]) -> int:
        """Parse pagination cursor to offset"""
        if not cursor:
            return 0
        try:
            import base64
            decoded = base64.b64decode(cursor).decode('utf-8')
            return int(decoded)
        except Exception:
            return 0
    
    def _create_cursor(self, offset: int) -> str:
        """Create pagination cursor from offset"""
        import base64
        encoded = base64.b64encode(str(offset).encode('utf-8')).decode('utf-8')
        return encoded


def create_recommendation_engine(db: Session, qdrant: QdrantManager) -> RecommendationEngine:
    """Factory function to create recommendation engine"""
    return RecommendationEngine(db, qdrant)
