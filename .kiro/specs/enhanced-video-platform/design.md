# Design Document

## Overview

The enhanced FreeWill video platform is a federated short-form video sharing application built on FastAPI with ActivityPub federation, AI-powered recommendations, and decentralized identity. The system processes user-uploaded videos through a multi-stage pipeline: upload validation, transcoding to multiple resolutions, AI feature extraction, and federation to remote instances. Content discovery is powered by vector similarity search using Qdrant, combining user preferences with engagement signals and recency factors.

The architecture follows a microservices-inspired pattern with clear separation between API layer, background workers, federation handlers, and AI services. All components communicate through Redis-backed task queues and share state via PostgreSQL. The design prioritizes scalability, fault tolerance, and compliance with ActivityPub specifications for seamless federation.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│  Routers Layer                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐      │
│  │  Posts   │ │  Users   │ │   Feed   │ │  Federation  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘      │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐       │
│  │ Upload Mgr   │ │  Auth/OAuth  │ │  Moderation Svc  │       │
│  └──────────────┘ └──────────────┘ └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Background Workers                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐       │
│  │ Media Worker │ │ AI Worker    │ │ Federation Worker│       │
│  │ - Transcode  │ │ - Embeddings │ │ - Delivery       │       │
│  │ - Thumbnails │ │ - Moderation │ │ - Inbox Process  │       │
│  └──────────────┘ └──────────────┘ └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data & Storage Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐      │
│  │PostgreSQL│ │  Redis   │ │  Qdrant  │ │ File Storage │      │
│  │- Posts   │ │- Queue   │ │- Vectors │ │ - uploads/   │      │
│  │- Users   │ │- Sessions│ │- Metadata│ │ - processed/ │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Federation Network                            │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │  Instance A  │◄───────►│  Instance B  │                     │
│  │  (Outbox)    │         │   (Inbox)    │                     │
│  └──────────────┘         └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Upload Flow:**
1. User uploads video via POST /api/posts with multipart form data
2. Upload manager validates format, size, duration
3. File saved to uploads/ directory, Upload Session created in Redis
4. Video Post record created in PostgreSQL with status="processing"
5. Transcoding task enqueued to Redis queue
6. Media worker processes video, generates resolutions and thumbnails
7. AI worker generates embeddings, stores in Qdrant
8. Video Post status updated to "ready"
9. Federation worker creates ActivityPub Create activity, delivers to followers

**Feed Generation Flow:**
1. User requests feed via GET /api/feed
2. Feed service retrieves user interaction history from PostgreSQL
3. Compute user preference embedding from liked/viewed videos
4. Query Qdrant for top 100 similar videos
5. Apply ranking formula: 0.6×similarity + 0.25×recency + 0.15×engagement
6. Return paginated results with cursor token

**Federation Inbox Flow:**
1. Remote instance POSTs ActivityPub activity to /api/federation/inbox
2. Verify HTTP Signature against sender's public key
3. Parse and validate activity structure
4. Route to appropriate handler (Create, Like, Announce, Delete, Move)
5. Process activity (download video, update counts, migrate followers)
6. Store activity in PostgreSQL for audit trail

## Components and Interfaces

### 1. Upload Manager (`app/services/upload_manager.py`)

**Responsibilities:**
- Validate video file format, size, and duration
- Manage chunked upload sessions
- Coordinate file storage and database record creation

**Interface:**
```python
class UploadManager:
    async def initiate_upload(
        self, 
        user_id: int, 
        filename: str, 
        file_size: int,
        total_chunks: int
    ) -> UploadSession
    
    async def upload_chunk(
        self,
        session_id: str,
        chunk_number: int,
        chunk_data: bytes
    ) -> ChunkStatus
    
    async def finalize_upload(
        self,
        session_id: str,
        metadata: VideoMetadata
    ) -> VideoPost
    
    async def validate_video_file(
        self,
        file_path: str
    ) -> ValidationResult
```

**Dependencies:**
- Redis for session state
- PostgreSQL for Video Post records
- File system for video storage

### 2. Media Worker (`app/workers/media.py`)

**Responsibilities:**
- Transcode videos to multiple resolutions
- Generate thumbnail images
- Update Video Post status

**Interface:**
```python
class MediaWorker:
    async def transcode_video(
        self,
        video_post_id: int,
        input_path: str
    ) -> TranscodeResult
    
    async def generate_thumbnails(
        self,
        video_path: str,
        output_dir: str
    ) -> List[ThumbnailInfo]
    
    async def process_video_task(
        self,
        task: VideoProcessingTask
    ) -> ProcessingResult
```

**Dependencies:**
- FFmpeg for video processing
- PostgreSQL for status updates
- File system for output storage

### 3. Embedding Service (`app/ai/embeddings.py`)

**Responsibilities:**
- Extract visual features from video frames
- Extract audio features if present
- Combine multimodal features with text metadata
- Generate normalized embedding vectors

**Interface:**
```python
class EmbeddingService:
    async def generate_video_embedding(
        self,
        video_post_id: int,
        video_path: str,
        metadata: VideoMetadata
    ) -> np.ndarray
    
    async def extract_visual_features(
        self,
        video_path: str,
        sample_rate: int = 1
    ) -> np.ndarray
    
    async def extract_audio_features(
        self,
        video_path: str
    ) -> Optional[np.ndarray]
    
    async def combine_features(
        self,
        visual: np.ndarray,
        audio: Optional[np.ndarray],
        text: np.ndarray
    ) -> np.ndarray
```

**Dependencies:**
- Pre-trained vision model (e.g., CLIP, VideoMAE)
- Audio feature extractor (e.g., VGGish)
- Text encoder (e.g., sentence-transformers)
- Qdrant client for storage

### 4. Recommendation Engine (`app/ai/recsys.py`)

**Responsibilities:**
- Compute user preference embeddings
- Query Qdrant for similar videos
- Apply ranking formula with multiple signals
- Handle cold-start scenarios

**Interface:**
```python
class RecommendationEngine:
    async def generate_feed(
        self,
        user_id: int,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> FeedResponse
    
    async def compute_user_embedding(
        self,
        user_id: int,
        lookback_days: int = 30
    ) -> Optional[np.ndarray]
    
    async def query_similar_videos(
        self,
        query_embedding: np.ndarray,
        limit: int = 100
    ) -> List[ScoredVideo]
    
    async def rank_videos(
        self,
        candidates: List[ScoredVideo],
        user_id: int
    ) -> List[RankedVideo]
    
    async def get_trending_videos(
        self,
        limit: int = 20
    ) -> List[VideoPost]
```

**Dependencies:**
- PostgreSQL for interaction history
- Qdrant for similarity search
- Redis for caching user embeddings

### 5. ActivityPub Service (`app/federation/activitypub.py`)

**Responsibilities:**
- Create ActivityPub objects and activities
- Sign activities with user private keys
- Validate incoming activities
- Convert between internal models and ActivityPub format

**Interface:**
```python
class ActivityPubService:
    def create_video_object(
        self,
        video_post: VideoPost
    ) -> Dict[str, Any]
    
    def create_activity(
        self,
        activity_type: str,
        actor: str,
        object: Dict[str, Any]
    ) -> Dict[str, Any]
    
    def sign_activity(
        self,
        activity: Dict[str, Any],
        private_key: str
    ) -> str
    
    def verify_signature(
        self,
        request_headers: Dict[str, str],
        request_body: bytes,
        public_key: str
    ) -> bool
    
    def parse_activity(
        self,
        activity_json: Dict[str, Any]
    ) -> Activity
```

**Dependencies:**
- Cryptography library for signing
- HTTP client for key retrieval
- PostgreSQL for activity storage

### 6. Inbox Handler (`app/federation/inbox.py`)

**Responsibilities:**
- Receive and validate incoming activities
- Route activities to appropriate processors
- Download and process federated videos
- Send responses to remote instances

**Interface:**
```python
class InboxHandler:
    async def handle_activity(
        self,
        activity: Dict[str, Any],
        signature: str
    ) -> InboxResponse
    
    async def process_create_activity(
        self,
        activity: Activity
    ) -> None
    
    async def process_like_activity(
        self,
        activity: Activity
    ) -> None
    
    async def process_announce_activity(
        self,
        activity: Activity
    ) -> None
    
    async def process_delete_activity(
        self,
        activity: Activity
    ) -> None
    
    async def process_move_activity(
        self,
        activity: Activity
    ) -> None
    
    async def download_federated_video(
        self,
        video_url: str,
        video_object: Dict[str, Any]
    ) -> str
```

**Dependencies:**
- ActivityPub service for validation
- HTTP client for downloads
- PostgreSQL for federated content storage
- Media worker for processing

### 7. Outbox Handler (`app/federation/outbox.py`)

**Responsibilities:**
- Publish local activities to followers
- Manage delivery queue and retries
- Track delivery status
- Handle delivery failures

**Interface:**
```python
class OutboxHandler:
    async def publish_activity(
        self,
        user_id: int,
        activity: Dict[str, Any]
    ) -> None
    
    async def deliver_to_inbox(
        self,
        inbox_url: str,
        activity: Dict[str, Any],
        private_key: str
    ) -> DeliveryResult
    
    async def get_follower_inboxes(
        self,
        user_id: int
    ) -> List[str]
    
    async def retry_failed_deliveries(
        self
    ) -> None
```

**Dependencies:**
- ActivityPub service for signing
- HTTP client for delivery
- PostgreSQL for follower lists and delivery tracking
- Redis for retry queue

### 8. Identity Service (`app/services/identity.py`)

**Responsibilities:**
- Generate and manage DIDs
- Encrypt/decrypt private keys
- Handle profile migration
- Export user data

**Interface:**
```python
class IdentityService:
    async def create_did(
        self,
        user_id: int,
        password: str
    ) -> DIDDocument
    
    async def encrypt_private_key(
        self,
        private_key: str,
        password: str
    ) -> str
    
    async def decrypt_private_key(
        self,
        encrypted_key: str,
        password: str
    ) -> str
    
    async def initiate_migration(
        self,
        user_id: int,
        new_instance_url: str
    ) -> MigrationToken
    
    async def export_user_data(
        self,
        user_id: int
    ) -> UserDataExport
```

**Dependencies:**
- Cryptography library for DID generation and encryption
- PostgreSQL for DID storage
- Outbox handler for Move activity delivery

### 9. Moderation Service (`app/services/moderation.py`)

**Responsibilities:**
- Scan videos for policy violations
- Flag inappropriate content
- Provide moderation interface for operators
- Handle federated content moderation

**Interface:**
```python
class ModerationService:
    async def scan_video(
        self,
        video_post_id: int,
        video_path: str
    ) -> ModerationResult
    
    async def flag_content(
        self,
        video_post_id: int,
        reason: str,
        severity: str
    ) -> None
    
    async def review_flagged_content(
        self,
        video_post_id: int,
        action: str,
        reviewer_id: int
    ) -> None
    
    async def reject_federated_content(
        self,
        video_post_id: int,
        origin_instance: str
    ) -> None
```

**Dependencies:**
- External moderation API (e.g., AWS Rekognition, Google Video Intelligence)
- PostgreSQL for moderation records
- Outbox handler for Reject activities

## Data Models

### VideoPost
```python
class VideoPost(Base):
    __tablename__ = "video_posts"
    
    id: int  # Primary key
    user_id: int  # Foreign key to users
    title: str  # Max 200 chars
    description: str  # Max 2000 chars
    tags: List[str]  # Max 10 tags
    duration: int  # Seconds
    status: str  # processing, ready, failed, rejected
    original_file_path: str
    thumbnail_small: str
    thumbnail_medium: str
    thumbnail_large: str
    resolutions: Dict[str, str]  # {360p: path, 480p: path, ...}
    is_federated: bool
    origin_instance: Optional[str]
    origin_actor_did: Optional[str]
    activitypub_id: Optional[str]
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    engagement_score: float  # Computed metric
    moderation_status: str  # pending, approved, flagged, rejected
    moderation_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
```

### UploadSession
```python
class UploadSession:
    session_id: str  # UUID
    user_id: int
    filename: str
    file_size: int
    total_chunks: int
    uploaded_chunks: Set[int]
    temp_file_path: str
    created_at: datetime
    expires_at: datetime
    status: str  # active, completed, expired, failed
```

### VideoEmbedding
```python
# Stored in Qdrant
class VideoEmbedding:
    id: int  # video_post_id
    vector: List[float]  # 512 dimensions
    payload: {
        "user_id": int,
        "created_at": str,
        "tags": List[str],
        "engagement_score": float,
        "is_federated": bool
    }
```

### Activity
```python
class Activity(Base):
    __tablename__ = "activities"
    
    id: int
    activity_id: str  # ActivityPub ID (URL)
    activity_type: str  # Create, Like, Announce, Delete, Move
    actor: str  # Actor DID or URL
    object_id: str  # Target object ID
    object_type: str  # Video, Note, etc.
    content: Dict[str, Any]  # Full ActivityPub JSON
    is_local: bool
    created_at: datetime
```

### DeliveryRecord
```python
class DeliveryRecord(Base):
    __tablename__ = "delivery_records"
    
    id: int
    activity_id: int  # Foreign key to activities
    inbox_url: str
    status: str  # pending, delivered, failed
    attempts: int
    last_attempt_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
```

### UserInteraction
```python
class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id: int
    user_id: int
    video_post_id: int
    interaction_type: str  # view, like, share, comment
    created_at: datetime
```

### ModerationRecord
```python
class ModerationRecord(Base):
    __tablename__ = "moderation_records"
    
    id: int
    video_post_id: int
    status: str  # pending, approved, flagged, rejected
    reason: Optional[str]
    severity: Optional[str]  # low, medium, high
    reviewer_id: Optional[int]
    reviewed_at: Optional[datetime]
    api_response: Optional[Dict[str, Any]]
    created_at: datetime
```

### DIDDocument
```python
class DIDDocument(Base):
    __tablename__ = "did_documents"
    
    id: int
    user_id: int  # Foreign key to users
    did: str  # did:key:...
    public_key: str
    encrypted_private_key: str
    current_instance_url: str
    previous_instance_url: Optional[str]
    migration_status: Optional[str]  # initiated, completed
    created_at: datetime
    updated_at: datetime
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Upload and Validation Properties

**Property 1: Format validation consistency**
*For any* uploaded file, the system should accept it if and only if its format is one of the supported codecs (MP4, WebM, MOV)
**Validates: Requirements 1.1**

**Property 2: File size boundary enforcement**
*For any* uploaded file, the system should reject it if its size exceeds 500MB and accept it otherwise
**Validates: Requirements 1.2**

**Property 3: Duration limit enforcement**
*For any* uploaded video, the system should reject it if its duration exceeds 180 seconds and accept it otherwise
**Validates: Requirements 1.3**

**Property 4: Upload session creation**
*For any* upload initiation, the system should create an Upload Session with a unique identifier and valid expiration timestamp
**Validates: Requirements 1.4**

**Property 5: Chunked upload integrity**
*For any* video uploaded in chunks, reassembling all chunks and computing the checksum should match the original file's checksum
**Validates: Requirements 1.5, 1.6**

**Property 6: Metadata validation boundaries**
*For any* video metadata, the system should reject it if title exceeds 200 characters, description exceeds 2000 characters, or tags exceed 10 items
**Validates: Requirements 1.7**

**Property 7: Upload completion persistence**
*For any* successfully completed upload, both a file in the uploads directory and a corresponding Video Post record in PostgreSQL should exist
**Validates: Requirements 1.8**

### Video Processing Properties

**Property 8: Transcoding task enqueueing**
*For any* newly created Video Post, a transcoding task should appear in the Media Worker queue
**Validates: Requirements 2.1**

**Property 9: Resolution variant generation**
*For any* video processed by the Media Worker, output files for all four resolutions (360p, 480p, 720p, 1080p) should exist
**Validates: Requirements 2.2**

**Property 10: Codec consistency**
*For any* transcoded video file, inspecting its codec should return H.264
**Validates: Requirements 2.3**

**Property 11: Thumbnail generation completeness**
*For any* processed video, three thumbnail files (small: 160x90, medium: 320x180, large: 640x360) should exist with correct dimensions
**Validates: Requirements 2.6**

**Property 12: Processing status transitions**
*For any* Video Post that completes transcoding successfully, its status should transition to "ready"
**Validates: Requirements 2.7**

**Property 13: Processing failure handling**
*For any* Video Post where transcoding fails, its status should be "failed" and an error message should be stored
**Validates: Requirements 2.8**

### Embedding and AI Properties

**Property 14: Embedding task triggering**
*For any* Video Post whose status changes to "ready", an embedding generation task should be enqueued
**Validates: Requirements 3.1**

**Property 15: Embedding dimensionality**
*For any* generated embedding vector, its dimensionality should be exactly 512 and its L2 norm should be 1.0 (normalized)
**Validates: Requirements 3.5**

**Property 16: Embedding storage round-trip**
*For any* embedding vector stored in Qdrant with a Video Post ID, retrieving by that ID should return the same vector and metadata payload
**Validates: Requirements 3.6, 3.7**

**Property 17: Embedding retry behavior**
*For any* embedding generation that fails, the system should retry up to 3 times before marking as failed
**Validates: Requirements 3.8**

### Recommendation Properties

**Property 18: Interaction history scope**
*For any* user feed request, the retrieved interaction history should only include interactions from the past 30 days
**Validates: Requirements 4.1**

**Property 19: User preference computation**
*For any* user with interaction history, the user preference embedding should be the normalized average of embeddings from positively-interacted videos
**Validates: Requirements 4.2**

**Property 20: Similarity search result count**
*For any* user preference embedding query to Qdrant, the number of returned candidates should not exceed 100
**Validates: Requirements 4.3**

**Property 21: Ranking formula correctness**
*For any* set of candidate videos, the final ranking score should equal (0.6 × similarity_score + 0.25 × recency_score + 0.15 × engagement_score)
**Validates: Requirements 4.5**

**Property 22: Cold-start fallback**
*For any* user with fewer than 5 interactions, the feed should return trending videos based on engagement from the past 24 hours
**Validates: Requirements 4.6**

**Property 23: Feed pagination consistency**
*For any* feed request, the response should contain exactly 20 videos (or fewer on the last page) and include a valid cursor token
**Validates: Requirements 4.7**

### Federation Publishing Properties

**Property 24: ActivityPub object structure**
*For any* Video Post with status "ready", the generated ActivityPub Create activity should include all required fields (name, content, published, url, mediaType, duration)
**Validates: Requirements 5.1, 5.2**

**Property 25: Resolution attachment completeness**
*For any* ActivityPub video object, the number of attachment objects should equal the number of successfully transcoded resolutions
**Validates: Requirements 5.3**

**Property 26: Signature verification round-trip**
*For any* ActivityPub activity signed with a user's private key, verifying the signature with the corresponding public key should succeed
**Validates: Requirements 5.4**

**Property 27: Delivery task creation**
*For any* signed activity, the number of enqueued delivery tasks should equal the number of follower inbox endpoints
**Validates: Requirements 5.5**

**Property 28: Delivery retry behavior**
*For any* delivery that receives a 4xx or 5xx error, the system should retry up to 5 times with exponentially increasing delays
**Validates: Requirements 5.8**

### Federation Receiving Properties

**Property 29: Signature validation enforcement**
*For any* incoming activity with an invalid or missing HTTP Signature, the inbox should reject it with a 401 status code
**Validates: Requirements 6.1, 6.2**

**Property 30: Federated content validation consistency**
*For any* federated video, the same size and duration limits that apply to local uploads should cause rejection if exceeded
**Validates: Requirements 6.5**

**Property 31: Federated content organization**
*For any* downloaded federated video, its file path should be in the federated content directory, not the local uploads directory
**Validates: Requirements 6.6**

**Property 32: Origin metadata preservation**
*For any* stored federated Video Post, the original author's DID and instance URL should be preserved in the database record
**Validates: Requirements 6.7**

**Property 33: Federated content rejection**
*For any* federated video that fails download or processing, a Reject activity should be sent to the origin instance
**Validates: Requirements 6.9**

### Federated Interaction Properties

**Property 34: Interaction activity creation**
*For any* user interaction (like, comment, share) on a federated Video Post, a corresponding ActivityPub activity should be created and delivered to the origin instance
**Validates: Requirements 7.1, 7.2, 7.3**

**Property 35: Interaction count aggregation**
*For any* Video Post, the displayed interaction counts should equal the sum of local interactions and federated interactions
**Validates: Requirements 7.8**

### Identity and Migration Properties

**Property 36: DID format compliance**
*For any* newly created user account, the generated DID should follow the did:key format with an Ed25519 key pair
**Validates: Requirements 8.1**

**Property 37: Key encryption round-trip**
*For any* private key encrypted with a user's password, decrypting with the same password should return the original key
**Validates: Requirements 8.2**

**Property 38: Actor DID inclusion**
*For any* user profile accessed via ActivityPub, the Actor object should include the user's DID in the "id" field
**Validates: Requirements 8.3**

**Property 39: Migration follower update**
*For any* verified Move activity, all follower records for the migrated user should be updated to point to the new instance URL
**Validates: Requirements 8.7**

**Property 40: Data export completeness**
*For any* user data export, all Video Posts and metadata should be included in ActivityPub format
**Validates: Requirements 8.8**

### Moderation Properties

**Property 41: Moderation scan triggering**
*For any* newly created Video Post, a moderation API scan should be initiated
**Validates: Requirements 9.1**

**Property 42: Flagged content exclusion**
*For any* Video Post flagged by moderation, it should not appear in public feed results
**Validates: Requirements 9.2**

**Property 43: Moderation consistency across sources**
*For any* video (local or federated), the same moderation rules should be applied
**Validates: Requirements 9.6**

**Property 44: Deletion completeness**
*For any* Video Post receiving a Delete activity, the video file, database record, and Qdrant embedding should all be removed
**Validates: Requirements 9.8**

### Error Handling Properties

**Property 45: Error response structure**
*For any* API endpoint error, the response should include an error code, message, and request ID
**Validates: Requirements 10.1**

**Property 46: Processing failure state**
*For any* failed video processing task, the Video Post status should be updated and the error message should be stored
**Validates: Requirements 10.3**

**Property 47: Database retry behavior**
*For any* transient database error, the system should retry the operation with exponential backoff
**Validates: Requirements 10.5**

**Property 48: Service fallback behavior**
*For any* Qdrant failure during feed generation, the system should fall back to recency-based ranking
**Validates: Requirements 10.7**

## Error Handling

### Upload Errors

**File Validation Failures:**
- Invalid format: Return 400 with error code `INVALID_FORMAT` and list of supported formats
- File too large: Return 413 with error code `FILE_TOO_LARGE` and maximum size
- Duration too long: Return 400 with error code `DURATION_EXCEEDED` and maximum duration
- Corrupted file: Return 400 with error code `CORRUPTED_FILE`

**Upload Session Errors:**
- Session expired: Return 410 with error code `SESSION_EXPIRED`
- Invalid chunk sequence: Return 400 with error code `INVALID_CHUNK_SEQUENCE`
- Checksum mismatch: Return 400 with error code `CHECKSUM_MISMATCH`

### Processing Errors

**Transcoding Failures:**
- FFmpeg error: Log full error, mark Video Post as "failed", notify user
- Insufficient disk space: Alert operators, pause processing queue
- Unsupported codec in source: Mark as "failed" with specific error message

**Embedding Generation Failures:**
- Model loading error: Retry with exponential backoff (1s, 2s, 4s)
- Feature extraction timeout: Retry up to 3 times, then mark as failed
- Qdrant connection error: Retry with backoff, alert if persistent

### Federation Errors

**Delivery Failures:**
- Network timeout: Retry with exponential backoff (1m, 5m, 15m, 1h, 4h)
- 4xx errors: Log and stop retrying (permanent failure)
- 5xx errors: Retry up to 5 times, then mark instance as unreachable
- Invalid response: Log full response, retry

**Inbox Processing Errors:**
- Invalid signature: Return 401, log attempt
- Malformed activity: Return 400 with validation errors
- Download failure: Send Reject activity to sender
- Storage failure: Return 500, retry processing

### Database Errors

**Connection Failures:**
- Connection pool exhausted: Wait and retry with timeout
- Connection lost: Automatic reconnection with exponential backoff
- Transaction deadlock: Retry transaction up to 3 times

**Query Failures:**
- Constraint violation: Return 400 with specific constraint error
- Timeout: Retry for read operations, fail fast for writes
- Data integrity error: Log full context, alert operators

### External Service Errors

**Redis Failures:**
- Connection lost: Fall back to database-backed sessions
- Command timeout: Retry once, then fall back
- Memory full: Alert operators, clear expired keys

**Qdrant Failures:**
- Connection error: Fall back to recency-based ranking
- Query timeout: Return cached results if available
- Index not found: Rebuild index, use fallback meanwhile

**Moderation API Failures:**
- API timeout: Retry once, then allow content with manual review flag
- Rate limit exceeded: Queue for later processing
- API error: Log error, flag for manual review

### Monitoring and Alerting

**Critical Alerts:**
- Database connection failures
- Persistent Qdrant failures
- Disk space below 10%
- Processing queue backed up > 1000 items
- Federation delivery success rate < 80%

**Warning Alerts:**
- Transcoding failures > 5% of attempts
- Embedding generation failures > 2% of attempts
- Average API response time > 500ms
- Redis memory usage > 80%

## Testing Strategy

### Unit Testing

**Framework:** pytest with pytest-asyncio for async tests

**Coverage Areas:**
- **Validation Functions:** Test format validation, size limits, duration limits with boundary values
- **Data Models:** Test model creation, validation, serialization
- **Utility Functions:** Test checksum calculation, file naming, metadata parsing
- **Error Handlers:** Test error response formatting, status code mapping

**Example Unit Tests:**
- Test that `validate_video_format()` accepts MP4/WebM/MOV and rejects others
- Test that `validate_file_size()` rejects files at 500MB + 1 byte
- Test that `generate_thumbnail_path()` follows naming convention
- Test that `compute_engagement_score()` handles zero values correctly

### Property-Based Testing

**Framework:** Hypothesis for Python

**Configuration:**
- Minimum 100 iterations per property test
- Use `@settings(max_examples=100)` decorator
- Enable database strategy for stateful testing
- Use custom strategies for domain models

**Property Test Categories:**

**1. Upload Properties:**
- Generate random video files with various formats, sizes, durations
- Test format validation accepts only supported codecs
- Test size and duration boundaries are enforced
- Test chunked upload reassembly produces correct checksums

**2. Processing Properties:**
- Generate random Video Post records
- Test that transcoding produces all required resolutions
- Test that thumbnail generation creates correct dimensions
- Test that status transitions follow valid state machine

**3. Embedding Properties:**
- Generate random video embeddings
- Test that all embeddings have exactly 512 dimensions
- Test that embeddings are normalized (L2 norm = 1.0)
- Test round-trip storage and retrieval from Qdrant

**4. Recommendation Properties:**
- Generate random user interaction histories
- Test that preference embeddings are correct averages
- Test that ranking formula weights are applied correctly
- Test that cold-start fallback triggers for new users

**5. Federation Properties:**
- Generate random ActivityPub activities
- Test signature round-trip (sign then verify)
- Test that activities include all required fields
- Test that delivery retries follow exponential backoff

**6. Identity Properties:**
- Generate random passwords and key pairs
- Test encryption/decryption round-trip
- Test DID format compliance
- Test that Move activities update follower records

**7. Moderation Properties:**
- Generate random video content
- Test that flagged content is excluded from feeds
- Test that moderation rules apply to both local and federated content
- Test that Delete activities remove all associated data

**Custom Strategies:**
```python
from hypothesis import strategies as st

# Video file strategy
video_files = st.builds(
    VideoFile,
    format=st.sampled_from(['mp4', 'webm', 'mov', 'avi', 'mkv']),
    size_mb=st.integers(min_value=1, max_value=600),
    duration_sec=st.integers(min_value=1, max_value=300)
)

# Video metadata strategy
video_metadata = st.builds(
    VideoMetadata,
    title=st.text(min_size=1, max_size=250),
    description=st.text(min_size=0, max_size=2500),
    tags=st.lists(st.text(min_size=1, max_size=50), max_size=15)
)

# Embedding vector strategy
embeddings = st.lists(
    st.floats(min_value=-1.0, max_value=1.0),
    min_size=512,
    max_size=512
).map(normalize_vector)

# ActivityPub activity strategy
activitypub_activities = st.builds(
    Activity,
    type=st.sampled_from(['Create', 'Like', 'Announce', 'Delete', 'Move']),
    actor=st.from_regex(r'https://[a-z]+\.com/users/[a-z]+'),
    object=st.dictionaries(
        st.sampled_from(['id', 'type', 'name', 'content']),
        st.text()
    )
)
```

### Integration Testing

**Test Scenarios:**
- End-to-end upload flow: Upload → Transcode → Embed → Federate
- Feed generation with real Qdrant queries
- Federation round-trip: Publish from Instance A → Receive at Instance B
- User migration: Create Move activity → Update followers → Export data
- Moderation workflow: Upload → Scan → Flag → Review → Reject

**Test Environment:**
- Docker Compose with PostgreSQL, Redis, Qdrant
- Mock external services (moderation API, remote instances)
- Test data fixtures for users, videos, interactions

### Performance Testing

**Load Tests:**
- Concurrent uploads: 100 simultaneous uploads
- Feed generation: 1000 requests/second
- Federation delivery: 10,000 activities/minute
- Embedding generation: 100 videos/minute

**Benchmarks:**
- Upload API response time < 200ms
- Feed generation < 500ms
- Transcoding time < 2x video duration
- Embedding generation < 30s per video

### Security Testing

**Authentication Tests:**
- Test JWT token validation
- Test OAuth2 flow
- Test DID-based authentication

**Authorization Tests:**
- Test that users can only modify their own content
- Test that moderation actions require operator role
- Test that private keys are never exposed in API responses

**Federation Security Tests:**
- Test HTTP Signature validation
- Test that unsigned activities are rejected
- Test that malformed activities don't cause crashes
- Test rate limiting on inbox endpoint

### Monitoring and Observability

**Metrics to Track:**
- Upload success/failure rates
- Transcoding queue depth and processing time
- Embedding generation success rate
- Feed generation latency (p50, p95, p99)
- Federation delivery success rate by instance
- API endpoint response times
- Database query performance
- Cache hit rates

**Logging Strategy:**
- Structured JSON logs with request IDs
- Log levels: DEBUG for development, INFO for production
- Sensitive data (passwords, private keys) never logged
- Full context for errors (stack traces, parameters)

**Tracing:**
- Distributed tracing for federation requests
- Trace IDs propagated across service boundaries
- Span annotations for key operations (transcode, embed, deliver)

