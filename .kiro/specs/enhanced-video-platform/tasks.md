# Implementation Plan

- [x] 1. Set up project structure and dependencies



  - Create FastAPI project structure with app/ directory
  - Set up requirements.txt with all dependencies (FastAPI, SQLAlchemy, Redis, Qdrant, FFmpeg-python, Hypothesis, pytest)
  - Create configuration management (config.py) for environment variables
  - Set up database models (models.py) with SQLAlchemy
  - Create Alembic migrations for database schema
  - Initialize Redis client (redis_client.py)
  - Initialize Qdrant client (ai/qdrant_client.py)
  - _Requirements: All_

- [ ]* 1.1 Write unit tests for configuration loading
  - Test environment variable parsing
  - Test default values
  - _Requirements: 10.1_

- [-] 2. Implement core data models and database schema





  - Create VideoPost model with all fields (status, resolutions, metadata, engagement metrics)
  - Create Activity model for ActivityPub activities
  - Create DeliveryRecord model for federation tracking
  - Create UserInteraction model for recommendation system
  - Create ModerationRecord model for content moderation
  - Create DIDDocument model for decentralized identity
  - Add database indexes for performance (user_id, created_at, status, activitypub_id)
  - _Requirements: 1.8, 5.1, 6.7, 8.1, 9.1_

- [ ]* 2.1 Write property test for data model validation
  - **Property 6: Metadata validation boundaries**
  - **Validates: Requirements 1.7**

- [ ]* 2.2 Write unit tests for model serialization
  - Test VideoPost to dict conversion
  - Test Activity JSON serialization
  - _Requirements: 1.8_

- [ ] 3. Implement upload manager and validation
  - Create UploadManager class (services/upload_manager.py)
  - Implement video format validation (MP4, WebM, MOV)
  - Implement file size validation (500MB limit)
  - Implement duration validation (180 seconds limit)
  - Create upload session management with Redis
  - Implement chunked upload support with progress tracking
  - Implement checksum verification for upload integrity
  - Create endpoint POST /api/posts/upload for video upload
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [ ]* 3.1 Write property test for format validation
  - **Property 1: Format validation consistency**
  - **Validates: Requirements 1.1**

- [ ]* 3.2 Write property test for file size validation
  - **Property 2: File size boundary enforcement**
  - **Validates: Requirements 1.2**

- [ ]* 3.3 Write property test for duration validation
  - **Property 3: Duration limit enforcement**
  - **Validates: Requirements 1.3**

- [ ]* 3.4 Write property test for chunked upload integrity
  - **Property 5: Chunked upload integrity**
  - **Validates: Requirements 1.5, 1.6**

- [ ]* 3.5 Write property test for upload completion persistence
  - **Property 7: Upload completion persistence**
  - **Validates: Requirements 1.8**

- [ ] 4. Implement media worker for video processing
  - Create MediaWorker class (workers/media.py)
  - Set up task queue with Redis and Celery/RQ
  - Implement FFmpeg wrapper for video transcoding
  - Implement multi-resolution transcoding (360p, 480p, 720p, 1080p) with H.264 codec
  - Implement thumbnail extraction at 2-second mark
  - Implement thumbnail generation in three sizes (160x90, 320x180, 640x360)
  - Implement status updates (processing → ready/failed)
  - Implement error handling and retry logic
  - Create task enqueuing on Video Post creation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

- [ ]* 4.1 Write property test for transcoding task enqueueing
  - **Property 8: Transcoding task enqueueing**
  - **Validates: Requirements 2.1**

- [ ]* 4.2 Write property test for resolution variant generation
  - **Property 9: Resolution variant generation**
  - **Validates: Requirements 2.2**

- [ ]* 4.3 Write property test for codec consistency
  - **Property 10: Codec consistency**
  - **Validates: Requirements 2.3**

- [ ]* 4.4 Write property test for thumbnail generation
  - **Property 11: Thumbnail generation completeness**
  - **Validates: Requirements 2.6**

- [ ]* 4.5 Write property test for processing status transitions
  - **Property 12: Processing status transitions**
  - **Validates: Requirements 2.7**

- [ ]* 4.6 Write unit tests for FFmpeg error handling
  - Test transcoding failures
  - Test corrupted video handling
  - _Requirements: 2.8_

- [ ] 5. Implement AI embedding service
  - Create EmbeddingService class (ai/embeddings.py)
  - Integrate pre-trained vision model (CLIP or VideoMAE) for visual features
  - Implement video frame sampling and feature extraction
  - Integrate audio feature extractor (VGGish) for audio features
  - Integrate text encoder (sentence-transformers) for metadata
  - Implement multimodal feature combination
  - Implement embedding normalization to 512 dimensions
  - Implement Qdrant storage with metadata payload
  - Implement retry logic with exponential backoff (3 attempts)
  - Create task enqueuing when Video Post status becomes "ready"
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ]* 5.1 Write property test for embedding task triggering
  - **Property 14: Embedding task triggering**
  - **Validates: Requirements 3.1**

- [ ]* 5.2 Write property test for embedding dimensionality
  - **Property 15: Embedding dimensionality**
  - **Validates: Requirements 3.5**

- [ ]* 5.3 Write property test for embedding storage round-trip
  - **Property 16: Embedding storage round-trip**
  - **Validates: Requirements 3.6, 3.7**

- [ ]* 5.4 Write property test for embedding retry behavior
  - **Property 17: Embedding retry behavior**
  - **Validates: Requirements 3.8**

- [ ] 6. Implement recommendation engine
  - Create RecommendationEngine class (ai/recsys.py)
  - Implement user interaction history retrieval (30-day lookback)
  - Implement user preference embedding computation (average of liked videos)
  - Implement Qdrant similarity search (top 100 candidates)
  - Implement recency boost calculation (exponential decay)
  - Implement ranking formula (0.6×similarity + 0.25×recency + 0.15×engagement)
  - Implement cold-start fallback (trending videos from past 24 hours)
  - Implement cursor-based pagination (20 videos per page)
  - Implement interaction recording and async embedding updates
  - Create endpoint GET /api/feed for personalized feed
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [ ]* 6.1 Write property test for interaction history scope
  - **Property 18: Interaction history scope**
  - **Validates: Requirements 4.1**

- [ ]* 6.2 Write property test for user preference computation
  - **Property 19: User preference computation**
  - **Validates: Requirements 4.2**

- [ ]* 6.3 Write property test for similarity search result count
  - **Property 20: Similarity search result count**
  - **Validates: Requirements 4.3**

- [ ]* 6.4 Write property test for ranking formula correctness
  - **Property 21: Ranking formula correctness**
  - **Validates: Requirements 4.5**

- [ ]* 6.5 Write property test for cold-start fallback
  - **Property 22: Cold-start fallback**
  - **Validates: Requirements 4.6**

- [ ]* 6.6 Write property test for feed pagination consistency
  - **Property 23: Feed pagination consistency**
  - **Validates: Requirements 4.7**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement ActivityPub service
  - Create ActivityPubService class (federation/activitypub.py)
  - Implement ActivityPub object creation for Video Posts
  - Implement Create activity generation with all required fields
  - Implement attachment objects for resolution variants
  - Implement HTTP Signatures signing with user private keys
  - Implement HTTP Signatures verification with public keys
  - Implement activity parsing and validation
  - Implement ActivityPub schema validation
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3_

- [ ]* 8.1 Write property test for ActivityPub object structure
  - **Property 24: ActivityPub object structure**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 8.2 Write property test for resolution attachment completeness
  - **Property 25: Resolution attachment completeness**
  - **Validates: Requirements 5.3**

- [ ]* 8.3 Write property test for signature verification round-trip
  - **Property 26: Signature verification round-trip**
  - **Validates: Requirements 5.4**

- [ ]* 8.4 Write unit tests for activity parsing
  - Test valid ActivityPub JSON parsing
  - Test malformed activity rejection
  - _Requirements: 6.3_

- [ ] 9. Implement outbox handler for federation publishing
  - Create OutboxHandler class (federation/outbox.py)
  - Implement follower inbox endpoint retrieval
  - Implement delivery task creation and enqueueing
  - Implement HTTP client for activity delivery with signature headers
  - Implement delivery status tracking (DeliveryRecord)
  - Implement retry logic with exponential backoff (5 attempts: 1m, 5m, 15m, 1h, 4h)
  - Implement 2xx success handling
  - Implement 4xx/5xx error handling
  - Create background worker for processing delivery queue
  - _Requirements: 5.5, 5.6, 5.7, 5.8_

- [ ]* 9.1 Write property test for delivery task creation
  - **Property 27: Delivery task creation**
  - **Validates: Requirements 5.5**

- [ ]* 9.2 Write property test for delivery retry behavior
  - **Property 28: Delivery retry behavior**
  - **Validates: Requirements 5.8**

- [ ]* 9.3 Write unit tests for delivery error handling
  - Test 4xx permanent failures
  - Test 5xx retry logic
  - _Requirements: 5.8_

- [ ] 10. Implement inbox handler for federation receiving
  - Create InboxHandler class (federation/inbox.py)
  - Implement HTTP Signature verification on incoming requests
  - Implement 401 rejection for invalid signatures
  - Implement activity routing (Create, Like, Announce, Delete, Move)
  - Implement Create activity processor for federated videos
  - Implement federated video download with size/duration validation
  - Implement federated content storage in separate directory
  - Implement origin metadata preservation (DID, instance URL)
  - Implement embedding generation for federated content
  - Implement Reject activity sending on failures
  - Create endpoint POST /api/federation/inbox
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

- [ ]* 10.1 Write property test for signature validation enforcement
  - **Property 29: Signature validation enforcement**
  - **Validates: Requirements 6.1, 6.2**

- [ ]* 10.2 Write property test for federated content validation
  - **Property 30: Federated content validation consistency**
  - **Validates: Requirements 6.5**

- [ ]* 10.3 Write property test for federated content organization
  - **Property 31: Federated content organization**
  - **Validates: Requirements 6.6**

- [ ]* 10.4 Write property test for origin metadata preservation
  - **Property 32: Origin metadata preservation**
  - **Validates: Requirements 6.7**

- [ ]* 10.5 Write property test for federated content rejection
  - **Property 33: Federated content rejection**
  - **Validates: Requirements 6.9**

- [ ] 11. Implement federated interaction handlers
  - Implement Like activity creation and delivery for federated posts
  - Implement Comment (Note) activity creation and delivery
  - Implement Share (Announce) activity creation and delivery
  - Implement Like activity receiver in inbox
  - Implement Note activity receiver in inbox
  - Implement Announce activity receiver in inbox
  - Implement interaction count aggregation (local + federated)
  - Update Video Post display to show aggregated counts
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

- [ ]* 11.1 Write property test for interaction activity creation
  - **Property 34: Interaction activity creation**
  - **Validates: Requirements 7.1, 7.2, 7.3**

- [ ]* 11.2 Write property test for interaction count aggregation
  - **Property 35: Interaction count aggregation**
  - **Validates: Requirements 7.8**

- [ ] 12. Implement identity service for DID management
  - Create IdentityService class (services/identity.py)
  - Implement DID generation using did:key method with Ed25519
  - Implement private key encryption with AES-256-GCM
  - Implement key derivation from user password (PBKDF2 or Argon2)
  - Implement private key decryption
  - Implement DID inclusion in ActivityPub Actor objects
  - Implement profile migration initiation (Move activity creation)
  - Implement Move activity signing and delivery
  - Implement Move activity verification in inbox
  - Implement follower record updates on migration
  - Implement user data export in ActivityPub format
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ]* 12.1 Write property test for DID format compliance
  - **Property 36: DID format compliance**
  - **Validates: Requirements 8.1**

- [ ]* 12.2 Write property test for key encryption round-trip
  - **Property 37: Key encryption round-trip**
  - **Validates: Requirements 8.2**

- [ ]* 12.3 Write property test for Actor DID inclusion
  - **Property 38: Actor DID inclusion**
  - **Validates: Requirements 8.3**

- [ ]* 12.4 Write property test for migration follower update
  - **Property 39: Migration follower update**
  - **Validates: Requirements 8.7**

- [ ]* 12.5 Write property test for data export completeness
  - **Property 40: Data export completeness**
  - **Validates: Requirements 8.8**

- [ ] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement moderation service
  - Create ModerationService class (services/moderation.py)
  - Integrate content moderation API (AWS Rekognition or Google Video Intelligence)
  - Implement video scanning on Video Post creation
  - Implement content flagging for policy violations
  - Implement creator notification on flagging
  - Implement moderation review interface for operators
  - Implement approve/reject/delete actions
  - Implement status updates (approved, rejected)
  - Implement federated content moderation
  - Implement Reject activity sending for policy violations
  - Implement Delete activity handling in inbox
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [ ]* 14.1 Write property test for moderation scan triggering
  - **Property 41: Moderation scan triggering**
  - **Validates: Requirements 9.1**

- [ ]* 14.2 Write property test for flagged content exclusion
  - **Property 42: Flagged content exclusion**
  - **Validates: Requirements 9.2**

- [ ]* 14.3 Write property test for moderation consistency
  - **Property 43: Moderation consistency across sources**
  - **Validates: Requirements 9.6**

- [ ]* 14.4 Write property test for deletion completeness
  - **Property 44: Deletion completeness**
  - **Validates: Requirements 9.8**

- [ ] 15. Implement comprehensive error handling
  - Implement structured error responses with error codes, messages, request IDs
  - Implement background task error logging with full context
  - Implement video processing failure handling
  - Implement federation delivery failure tracking
  - Implement database retry logic with exponential backoff
  - Implement Redis fallback to database-backed sessions
  - Implement Qdrant fallback to recency-based ranking
  - Implement metrics emission for critical errors
  - Create custom exception classes for domain errors
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

- [ ]* 15.1 Write property test for error response structure
  - **Property 45: Error response structure**
  - **Validates: Requirements 10.1**

- [ ]* 15.2 Write property test for processing failure state
  - **Property 46: Processing failure state**
  - **Validates: Requirements 10.3**

- [ ]* 15.3 Write property test for database retry behavior
  - **Property 47: Database retry behavior**
  - **Validates: Requirements 10.5**

- [ ]* 15.4 Write property test for service fallback behavior
  - **Property 48: Service fallback behavior**
  - **Validates: Requirements 10.7**

- [ ] 16. Implement API routers and endpoints
  - Create posts router (routers/posts.py) with upload, get, list, delete endpoints
  - Create feed router (routers/feed.py) with personalized feed endpoint
  - Create federation router (routers/federation.py) with inbox and outbox endpoints
  - Create users router (routers/users.py) with profile, migration, export endpoints
  - Implement authentication middleware (JWT + OAuth2)
  - Implement rate limiting on endpoints
  - Implement request validation with Pydantic schemas
  - Implement response serialization
  - Wire all routers into main.py
  - _Requirements: All_

- [ ]* 16.1 Write integration tests for upload flow
  - Test end-to-end upload → transcode → embed → federate
  - _Requirements: 1.8, 2.7, 3.6, 5.5_

- [ ]* 16.2 Write integration tests for feed generation
  - Test feed with real Qdrant queries
  - _Requirements: 4.7_

- [ ]* 16.3 Write integration tests for federation round-trip
  - Test publish from Instance A → receive at Instance B
  - _Requirements: 5.7, 6.8_

- [ ] 17. Set up monitoring and observability
  - Implement structured JSON logging with request IDs
  - Implement metrics collection (upload rates, processing times, delivery success)
  - Implement distributed tracing for federation requests
  - Set up health check endpoints
  - Configure log levels (DEBUG for dev, INFO for prod)
  - Implement sensitive data filtering in logs
  - Create monitoring dashboards for key metrics
  - Set up alerting for critical errors
  - _Requirements: 10.8_

- [ ] 18. Create deployment configuration
  - Create Dockerfile for FastAPI application
  - Create docker-compose.yml with PostgreSQL, Redis, Qdrant services
  - Create environment variable templates (.env.example)
  - Create database migration scripts
  - Create worker startup scripts
  - Document deployment process in README.md
  - _Requirements: All_

- [ ] 19. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
