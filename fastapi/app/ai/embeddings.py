"""
AI Embedding Service
Generates multimodal embeddings for video content using vision, audio, and text models
Requirements: 3.1-3.8
"""

import numpy as np
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import time
import subprocess
import json
import tempfile
import os

from sqlalchemy.orm import Session
from app.config import settings
from app.models import VideoPost
from app.schemas import EmbeddingResult
from app.ai.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)

# Real model imports
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, using simulated text features")

try:
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("transformers/CLIP not available, using simulated vision features")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class EmbeddingService:
    """
    Service for generating and storing video embeddings
    Combines visual, audio, and text features into a single normalized vector
    """
    
    def __init__(self, db: Session, qdrant: QdrantManager):
        self.db = db
        self.qdrant = qdrant
        self.target_dimension = settings.EMBEDDING_DIMENSION  # 512
        
        # Initialize real models
        self.vision_model_name = settings.VISION_MODEL_NAME
        self.text_model_name = settings.TEXT_MODEL_NAME
        
        # Load text model (sentence-transformers)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading text model: {self.text_model_name}")
                self.text_model = SentenceTransformer(self.text_model_name)
                logger.info("✓ Text model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load text model: {e}")
                self.text_model = None
        else:
            self.text_model = None
        
        # Load vision model (CLIP or Ollama)
        self.use_ollama = settings.USE_OLLAMA
        self.ollama_url = settings.OLLAMA_URL
        self.ollama_model = settings.OLLAMA_MODEL
        
        if self.use_ollama:
            logger.info(f"Using Ollama for vision: {self.ollama_model} at {self.ollama_url}")
            self.clip_model = None
            self.clip_processor = None
        elif CLIP_AVAILABLE:
            try:
                logger.info(f"Loading vision model: {self.vision_model_name}")
                self.clip_model = CLIPModel.from_pretrained(self.vision_model_name)
                self.clip_processor = CLIPProcessor.from_pretrained(self.vision_model_name)
                logger.info("✓ Vision model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load vision model: {e}")
                self.clip_model = None
                self.clip_processor = None
        else:
            self.clip_model = None
            self.clip_processor = None
    
    def extract_visual_features(
        self,
        video_path: str,
        sample_rate: int = 1
    ) -> np.ndarray:
        """
        Extract visual features from video frames
        Requirements: 3.2
        
        Args:
            video_path: Path to video file
            sample_rate: Extract 1 frame per N seconds
            
        Returns:
            Averaged visual feature vector
        """
        try:
            # Get video duration
            duration = self._get_video_duration(video_path)
            if duration <= 0:
                logger.warning(f"Could not determine video duration for {video_path}")
                return np.zeros(512)
            
            # Sample frames at regular intervals
            num_samples = max(1, int(duration / sample_rate))
            timestamps = np.linspace(0, duration - 1, num_samples)
            
            features = []
            
            for timestamp in timestamps:
                # Extract frame at timestamp
                frame_path = self._extract_frame(video_path, timestamp)
                if frame_path:
                    # In production: Use CLIP or VideoMAE to extract features
                    # For now: Generate simulated features
                    feature = self._simulate_vision_features(frame_path)
                    features.append(feature)
                    
                    # Clean up temp frame
                    try:
                        os.remove(frame_path)
                    except:
                        pass
            
            if not features:
                logger.warning(f"No visual features extracted from {video_path}")
                return np.zeros(512)
            
            # Average features across all frames
            avg_features = np.mean(features, axis=0)
            
            logger.info(f"Extracted visual features from {len(features)} frames")
            return avg_features
            
        except Exception as e:
            logger.error(f"Error extracting visual features: {e}")
            return np.zeros(512)
    
    def extract_audio_features(
        self,
        video_path: str
    ) -> Optional[np.ndarray]:
        """
        Extract audio features if audio track exists
        Requirements: 3.3
        
        Args:
            video_path: Path to video file
            
        Returns:
            Audio feature vector or None if no audio
        """
        try:
            # Check if video has audio track
            has_audio = self._has_audio_track(video_path)
            
            if not has_audio:
                logger.info(f"No audio track in {video_path}")
                return None
            
            # Extract audio to temporary file
            audio_path = self._extract_audio(video_path)
            if not audio_path:
                return None
            
            # In production: Use VGGish or similar to extract audio features
            # For now: Generate simulated features
            audio_features = self._simulate_audio_features(audio_path)
            
            # Clean up temp audio file
            try:
                os.remove(audio_path)
            except:
                pass
            
            logger.info(f"Extracted audio features from {video_path}")
            return audio_features
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            return None
    
    def extract_text_features(
        self,
        title: str,
        description: Optional[str],
        tags: List[str]
    ) -> np.ndarray:
        """
        Extract text features from metadata
        Requirements: 3.4
        
        Args:
            title: Video title
            description: Video description
            tags: List of tags
            
        Returns:
            Text feature vector
        """
        try:
            # Combine all text
            text_parts = [title]
            if description:
                text_parts.append(description)
            if tags:
                text_parts.extend(tags)
            
            combined_text = " ".join(text_parts)
            
            # In production: Use sentence-transformers to encode text
            # For now: Generate simulated features based on text
            text_features = self._simulate_text_features(combined_text)
            
            logger.info(f"Extracted text features from metadata")
            return text_features
            
        except Exception as e:
            logger.error(f"Error extracting text features: {e}")
            return np.zeros(512)
    
    def combine_features(
        self,
        visual: np.ndarray,
        audio: Optional[np.ndarray],
        text: np.ndarray
    ) -> np.ndarray:
        """
        Combine multimodal features into single vector
        Requirements: 3.4
        
        Args:
            visual: Visual feature vector
            audio: Audio feature vector (optional)
            text: Text feature vector
            
        Returns:
            Combined feature vector
        """
        try:
            # Weight the different modalities
            # Visual: 50%, Text: 30%, Audio: 20%
            if audio is not None:
                combined = (
                    0.5 * visual +
                    0.3 * text +
                    0.2 * audio
                )
            else:
                # No audio: Visual 60%, Text 40%
                combined = (
                    0.6 * visual +
                    0.4 * text
                )
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining features: {e}")
            # Fallback to visual features
            return visual
    
    def normalize_embedding(
        self,
        embedding: np.ndarray
    ) -> np.ndarray:
        """
        Normalize embedding to target dimension and L2 norm = 1.0
        Requirements: 3.5
        
        Args:
            embedding: Raw embedding vector
            
        Returns:
            Normalized 512-dimensional vector with L2 norm = 1.0
        """
        try:
            # Ensure correct dimension
            if len(embedding) != self.target_dimension:
                if len(embedding) > self.target_dimension:
                    # Truncate
                    embedding = embedding[:self.target_dimension]
                else:
                    # Pad with zeros
                    padding = np.zeros(self.target_dimension - len(embedding))
                    embedding = np.concatenate([embedding, padding])
            
            # L2 normalization
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            else:
                # Handle zero vector
                logger.warning("Zero embedding vector, using random normalized vector")
                embedding = np.random.randn(self.target_dimension)
                embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error normalizing embedding: {e}")
            # Return random normalized vector as fallback
            embedding = np.random.randn(self.target_dimension)
            return embedding / np.linalg.norm(embedding)
    
    async def generate_video_embedding(
        self,
        video_post_id: int,
        video_path: str,
        metadata: Dict[str, Any]
    ) -> EmbeddingResult:
        """
        Generate complete embedding for a video
        Requirements: 3.1-3.6
        
        Args:
            video_post_id: Video post ID
            video_path: Path to video file
            metadata: Video metadata (title, description, tags)
            
        Returns:
            EmbeddingResult with success status and embedding
        """
        try:
            logger.info(f"Generating embedding for video {video_post_id}")
            
            # Extract visual features
            visual_features = self.extract_visual_features(video_path)
            
            # Extract audio features
            audio_features = self.extract_audio_features(video_path)
            
            # Extract text features
            text_features = self.extract_text_features(
                title=metadata.get('title', ''),
                description=metadata.get('description'),
                tags=metadata.get('tags', [])
            )
            
            # Combine features
            combined = self.combine_features(visual_features, audio_features, text_features)
            
            # Normalize to 512 dimensions with L2 norm = 1.0
            embedding = self.normalize_embedding(combined)
            
            # Verify dimensions and normalization
            assert len(embedding) == self.target_dimension, f"Wrong dimension: {len(embedding)}"
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01, f"Not normalized: {norm}"
            
            logger.info(f"✓ Generated embedding for video {video_post_id} (dim={len(embedding)}, norm={norm:.4f})")
            
            return EmbeddingResult(
                success=True,
                embedding=embedding.tolist(),
                dimension=len(embedding)
            )
            
        except Exception as e:
            logger.error(f"Error generating embedding for video {video_post_id}: {e}")
            return EmbeddingResult(
                success=False,
                error=str(e)
            )
    
    async def store_embedding(
        self,
        video_post_id: int,
        embedding: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """
        Store embedding in Qdrant with retry logic
        Requirements: 3.6, 3.7, 3.8
        
        Args:
            video_post_id: Video post ID
            embedding: Normalized embedding vector
            payload: Metadata payload
            
        Returns:
            True if successful, False otherwise
        """
        max_attempts = settings.EMBEDDING_RETRY_ATTEMPTS
        backoff_sec = settings.EMBEDDING_RETRY_BACKOFF_SEC
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Storing embedding for video {video_post_id} (attempt {attempt}/{max_attempts})")
                
                self.qdrant.upsert_embedding(
                    video_post_id=video_post_id,
                    embedding=embedding,
                    payload=payload
                )
                
                logger.info(f"✓ Stored embedding for video {video_post_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to store embedding (attempt {attempt}/{max_attempts}): {e}")
                
                if attempt < max_attempts:
                    # Exponential backoff
                    sleep_time = backoff_sec * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to store embedding after {max_attempts} attempts")
                    return False
        
        return False
    
    async def process_video_embedding(
        self,
        video_post_id: int
    ) -> bool:
        """
        Complete embedding pipeline: generate and store
        Requirements: 3.1-3.8
        
        Args:
            video_post_id: Video post ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get video post
            video_post = self.db.query(VideoPost).filter(
                VideoPost.id == video_post_id
            ).first()
            
            if not video_post:
                logger.error(f"Video post {video_post_id} not found")
                return False
            
            # Check if video is ready
            if video_post.status != "ready":
                logger.warning(f"Video {video_post_id} is not ready (status: {video_post.status})")
                return False
            
            # Get video path (use highest resolution available)
            video_path = None
            if video_post.resolutions:
                # Try resolutions in order of preference
                for res in ['1080p', '720p', '480p', '360p']:
                    if res in video_post.resolutions:
                        video_path = video_post.resolutions[res]
                        break
            
            if not video_path:
                video_path = video_post.original_file_path
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Video file not found for post {video_post_id}")
                return False
            
            # Prepare metadata
            metadata = {
                'title': video_post.title,
                'description': video_post.description,
                'tags': video_post.tags or []
            }
            
            # Generate embedding
            result = await self.generate_video_embedding(
                video_post_id=video_post_id,
                video_path=video_path,
                metadata=metadata
            )
            
            if not result.success:
                logger.error(f"Failed to generate embedding: {result.error}")
                return False
            
            # Prepare payload for Qdrant
            payload = {
                'user_id': video_post.user_id,
                'created_at': video_post.created_at.isoformat(),
                'tags': video_post.tags or [],
                'engagement_score': video_post.engagement_score,
                'is_federated': video_post.is_federated,
                'title': video_post.title
            }
            
            # Store in Qdrant with retry logic
            success = await self.store_embedding(
                video_post_id=video_post_id,
                embedding=result.embedding,
                payload=payload
            )
            
            if success:
                logger.info(f"✓ Successfully processed embedding for video {video_post_id}")
            else:
                logger.error(f"Failed to store embedding for video {video_post_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing video embedding {video_post_id}: {e}")
            return False
    
    # Helper methods for feature extraction
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds"""
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get('format', {}).get('duration', 0))
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
        return 0
    
    def _extract_frame(self, video_path: str, timestamp: float) -> Optional[str]:
        """Extract a single frame at timestamp"""
        try:
            # Create temp file for frame
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            
            cmd = [
                settings.FFMPEG_PATH,
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0 and os.path.exists(temp_path):
                return temp_path
            
            # Clean up on failure
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error extracting frame: {e}")
        
        return None
    
    def _has_audio_track(self, video_path: str) -> bool:
        """Check if video has audio track"""
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'json',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return len(data.get('streams', [])) > 0
        except Exception as e:
            logger.error(f"Error checking audio track: {e}")
        return False
    
    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio to temporary file"""
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(temp_fd)
            
            cmd = [
                settings.FFMPEG_PATH,
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and os.path.exists(temp_path):
                return temp_path
            
            # Clean up on failure
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
        
        return None
    
    # Simulation methods (replace with real models in production)
    
    def _simulate_vision_features(self, frame_path: str) -> np.ndarray:
        """
        Extract vision features using CLIP, Ollama, or simulate if not available
        """
        # Try Ollama first if enabled
        if self.use_ollama and REQUESTS_AVAILABLE:
            try:
                features = self._extract_ollama_features(frame_path)
                if features is not None:
                    return features
            except Exception as e:
                logger.error(f"Error using Ollama: {e}, falling back to CLIP or simulation")
        
        # Try CLIP model
        if self.clip_model is not None and self.clip_processor is not None:
            try:
                image = Image.open(frame_path).convert('RGB')
                inputs = self.clip_processor(images=image, return_tensors="pt")
                
                # Get image features
                image_features = self.clip_model.get_image_features(**inputs)
                features = image_features.detach().numpy()[0]
                
                # Normalize
                return features / np.linalg.norm(features)
            except Exception as e:
                logger.error(f"Error using CLIP model: {e}, falling back to simulation")
        
        # Fallback: Generate deterministic features based on file
        seed = hash(frame_path) % (2**32)
        np.random.seed(seed)
        features = np.random.randn(512)
        return features / np.linalg.norm(features)
    
    def _extract_ollama_features(self, frame_path: str) -> Optional[np.ndarray]:
        """
        Extract vision features using Ollama (e.g., SmolVLM)
        """
        try:
            import base64
            
            # Read and encode image
            with open(frame_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": "Describe this image in detail.",
                    "images": [image_data],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                description = result.get('response', '')
                
                # Use text model to encode the description
                if self.text_model is not None:
                    embedding = self.text_model.encode(description, convert_to_numpy=True)
                    
                    # Ensure 512 dimensions
                    if len(embedding) != 512:
                        if len(embedding) > 512:
                            embedding = embedding[:512]
                        else:
                            padding = np.zeros(512 - len(embedding))
                            embedding = np.concatenate([embedding, padding])
                    
                    # Normalize
                    return embedding / np.linalg.norm(embedding)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Ollama features: {e}")
            return None
    
    def _simulate_audio_features(self, audio_path: str) -> np.ndarray:
        """
        Simulate audio model feature extraction
        In production: Use VGGish or similar
        """
        # Generate deterministic features based on file
        seed = hash(audio_path) % (2**32)
        np.random.seed(seed)
        features = np.random.randn(512)
        return features / np.linalg.norm(features)
    
    def _simulate_text_features(self, text: str) -> np.ndarray:
        """
        Extract text features using sentence-transformers or simulate if not available
        """
        # Try real sentence-transformers model first
        if self.text_model is not None:
            try:
                # Encode text to get embedding
                embedding = self.text_model.encode(text, convert_to_numpy=True)
                
                # Ensure 512 dimensions
                if len(embedding) != 512:
                    if len(embedding) > 512:
                        embedding = embedding[:512]
                    else:
                        padding = np.zeros(512 - len(embedding))
                        embedding = np.concatenate([embedding, padding])
                
                # Normalize
                return embedding / np.linalg.norm(embedding)
            except Exception as e:
                logger.error(f"Error using sentence-transformers: {e}, falling back to simulation")
        
        # Fallback: Generate deterministic features based on text
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        features = np.random.randn(512)
        return features / np.linalg.norm(features)


def create_embedding_service(db: Session, qdrant: QdrantManager) -> EmbeddingService:
    """Factory function to create embedding service"""
    return EmbeddingService(db, qdrant)
