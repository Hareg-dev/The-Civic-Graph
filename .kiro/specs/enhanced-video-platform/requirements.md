# Requirements Document

## Introduction

This document specifies requirements for enhancing the FreeWill federated short video sharing platform with comprehensive video upload capabilities, advanced recommendation algorithms, and robust ActivityPub federation features. The system enables users to upload, process, and share short-form videos across federated instances while providing personalized content discovery through AI-powered recommendations.

## Glossary

- **Video Platform**: The FreeWill short video sharing application
- **User**: An authenticated individual who can create, view, and interact with video content
- **Video Post**: A short-form video content item with metadata, stored in PostgreSQL
- **Upload Session**: A temporary state tracking multi-part video upload progress
- **Media Worker**: Background process responsible for video transcoding and processing
- **Embedding**: A vector representation of video content used for similarity matching
- **Qdrant**: Vector database used for storing and querying video embeddings
- **ActivityPub Object**: A federated content representation following ActivityPub specification
- **Inbox**: An endpoint receiving federated activities from other instances
- **Outbox**: An endpoint publishing local activities to federated instances
- **DID**: Decentralized Identifier for portable user identity
- **Instance**: A single deployment of the Video Platform
- **Federation**: The network of interconnected Video Platform instances
- **Recommendation Engine**: AI-powered system for ranking and suggesting video content
- **Transcoding**: Process of converting uploaded videos to standardized formats and resolutions
- **Thumbnail**: Static image extracted from video for preview purposes
- **Content Moderation**: System for filtering inappropriate or policy-violating content

## Requirements

### Requirement 1

**User Story:** As a content creator, I want to upload short videos with metadata, so that I can share my content with followers across federated instances.

#### Acceptance Criteria

1. WHEN a User initiates a video upload, THE Video Platform SHALL validate the file format against supported video codecs (MP4, WebM, MOV)
2. WHEN a User uploads a video file, THE Video Platform SHALL enforce a maximum file size limit of 500MB
3. WHEN a User uploads a video, THE Video Platform SHALL enforce a maximum duration limit of 180 seconds
4. WHEN a video upload begins, THE Video Platform SHALL create an Upload Session with a unique identifier and expiration timestamp
5. WHERE chunked upload is selected, THE Video Platform SHALL accept video data in sequential chunks and track completion progress
6. WHEN all video chunks are received, THE Video Platform SHALL validate file integrity using checksum verification
7. WHEN a User provides video metadata (title, description, tags), THE Video Platform SHALL validate each field against length constraints (title: 200 chars, description: 2000 chars, tags: 10 maximum)
8. WHEN a video upload completes successfully, THE Video Platform SHALL store the raw video file in the uploads directory and create a Video Post record in PostgreSQL

### Requirement 2

**User Story:** As a content creator, I want my uploaded videos to be automatically processed and optimized, so that viewers can watch them smoothly on any device.

#### Acceptance Criteria

1. WHEN a Video Post is created, THE Video Platform SHALL enqueue a transcoding task to the Media Worker queue
2. WHEN the Media Worker processes a video, THE Video Platform SHALL generate multiple resolution variants (360p, 480p, 720p, 1080p)
3. WHEN the Media Worker transcodes video, THE Video Platform SHALL use H.264 codec for maximum compatibility
4. WHEN transcoding completes for each resolution, THE Video Platform SHALL store the output file with a standardized naming convention
5. WHEN the Media Worker processes a video, THE Video Platform SHALL extract a thumbnail image at the 2-second mark
6. WHEN the Media Worker generates a thumbnail, THE Video Platform SHALL create three thumbnail sizes (small: 160x90, medium: 320x180, large: 640x360)
7. WHEN all transcoding tasks complete successfully, THE Video Platform SHALL update the Video Post status to "ready"
8. IF transcoding fails for any resolution, THEN THE Video Platform SHALL log the error, mark the Video Post status as "failed", and notify the User

### Requirement 3

**User Story:** As a content creator, I want my videos to be analyzed for content understanding, so that the platform can recommend them to interested viewers.

#### Acceptance Criteria

1. WHEN a Video Post status changes to "ready", THE Video Platform SHALL enqueue an embedding generation task
2. WHEN the embedding worker processes a video, THE Video Platform SHALL extract visual features using a pre-trained vision model
3. WHEN the embedding worker processes a video, THE Video Platform SHALL extract audio features if audio track exists
4. WHEN the embedding worker processes a video, THE Video Platform SHALL combine text metadata (title, description, tags) with visual and audio features
5. WHEN feature extraction completes, THE Video Platform SHALL generate a normalized embedding vector of 512 dimensions
6. WHEN an embedding vector is generated, THE Video Platform SHALL store it in Qdrant with the Video Post identifier as the point ID
7. WHEN storing in Qdrant, THE Video Platform SHALL include metadata payload (user_id, created_at, tags, engagement_score)
8. IF embedding generation fails, THEN THE Video Platform SHALL retry up to 3 times with exponential backoff before marking as failed

### Requirement 4

**User Story:** As a viewer, I want to see a personalized feed of videos ranked by relevance, so that I discover content matching my interests.

#### Acceptance Criteria

1. WHEN a User requests their feed, THE Video Platform SHALL retrieve the User's interaction history (views, likes, shares) from the past 30 days
2. WHEN generating feed recommendations, THE Video Platform SHALL compute a user preference embedding by averaging embeddings of positively-interacted videos
3. WHEN a user preference embedding exists, THE Video Platform SHALL query Qdrant for the top 100 similar videos using cosine similarity
4. WHEN Qdrant returns candidate videos, THE Video Platform SHALL apply a recency boost factor that decreases exponentially with video age
5. WHEN ranking videos, THE Video Platform SHALL combine similarity score (weight: 0.6), recency score (weight: 0.25), and engagement score (weight: 0.15)
6. WHEN a User has insufficient interaction history, THE Video Platform SHALL fall back to trending videos based on engagement metrics from the past 24 hours
7. WHEN returning feed results, THE Video Platform SHALL paginate with 20 videos per page and include cursor-based pagination tokens
8. WHEN a User views a video from their feed, THE Video Platform SHALL record the interaction and update the user preference embedding asynchronously

### Requirement 5

**User Story:** As a content creator, I want my videos to be federated to other instances, so that my content reaches a wider audience across the network.

#### Acceptance Criteria

1. WHEN a Video Post status changes to "ready", THE Video Platform SHALL create an ActivityPub Create activity with the video as the object
2. WHEN creating an ActivityPub object, THE Video Platform SHALL include video metadata (name, content, published, url, mediaType, duration)
3. WHEN creating an ActivityPub object, THE Video Platform SHALL include attachment objects for each resolution variant with proper mediaType and URL
4. WHEN an ActivityPub activity is created, THE Video Platform SHALL sign it using the User's private key following HTTP Signatures specification
5. WHEN an activity is signed, THE Video Platform SHALL enqueue delivery tasks to all follower instances' inbox endpoints
6. WHEN delivering to a remote inbox, THE Video Platform SHALL include the HTTP Signature header and Date header
7. WHEN a remote inbox returns a 2xx status code, THE Video Platform SHALL mark the delivery as successful
8. IF a remote inbox returns a 4xx or 5xx error, THEN THE Video Platform SHALL retry delivery up to 5 times with exponential backoff

### Requirement 6

**User Story:** As an instance operator, I want to receive and process federated videos from other instances, so that my users can discover content from across the network.

#### Acceptance Criteria

1. WHEN a remote instance POSTs to the Inbox endpoint, THE Video Platform SHALL verify the HTTP Signature against the sender's public key
2. IF the HTTP Signature is invalid or missing, THEN THE Video Platform SHALL reject the request with a 401 status code
3. WHEN the Inbox receives a Create activity with a Video object, THE Video Platform SHALL validate the activity structure against ActivityPub schema
4. WHEN processing a federated Video object, THE Video Platform SHALL download the video file from the provided URL
5. WHEN downloading a federated video, THE Video Platform SHALL enforce the same size and duration limits as local uploads
6. WHEN a federated video is downloaded, THE Video Platform SHALL store it in a separate federated content directory
7. WHEN storing a federated Video Post, THE Video Platform SHALL preserve the original author's DID and instance URL
8. WHEN a federated Video Post is stored, THE Video Platform SHALL enqueue an embedding generation task to include it in recommendations
9. IF downloading or processing a federated video fails, THEN THE Video Platform SHALL log the error and send a Reject activity to the sender

### Requirement 7

**User Story:** As a viewer, I want to interact with federated videos (like, comment, share), so that I can engage with content from any instance.

#### Acceptance Criteria

1. WHEN a User likes a federated Video Post, THE Video Platform SHALL create a Like activity and deliver it to the origin instance's inbox
2. WHEN a User comments on a federated Video Post, THE Video Platform SHALL create a Note object and wrap it in a Create activity for delivery
3. WHEN a User shares a federated Video Post, THE Video Platform SHALL create an Announce activity and deliver it to followers
4. WHEN creating activities for federated content, THE Video Platform SHALL include the original object's ID as the target
5. WHEN the Inbox receives a Like activity for a local Video Post, THE Video Platform SHALL increment the like count and store the activity
6. WHEN the Inbox receives a Note in reply to a local Video Post, THE Video Platform SHALL create a comment record linked to the Video Post
7. WHEN the Inbox receives an Announce activity, THE Video Platform SHALL record the share and update engagement metrics
8. WHEN displaying a Video Post, THE Video Platform SHALL aggregate interaction counts from both local and federated sources

### Requirement 8

**User Story:** As a user, I want my identity to be portable across instances, so that I can migrate my profile and content without losing my followers.

#### Acceptance Criteria

1. WHEN a User account is created, THE Video Platform SHALL generate a DID using the did:key method with an Ed25519 key pair
2. WHEN a User account is created, THE Video Platform SHALL store the private key encrypted using AES-256-GCM with a key derived from the user's password
3. WHEN a User profile is accessed, THE Video Platform SHALL include the DID in the ActivityPub Actor object as the "id" field
4. WHEN a User initiates profile migration, THE Video Platform SHALL create a Move activity referencing the new instance URL
5. WHEN a Move activity is created, THE Video Platform SHALL sign it with the User's private key and deliver it to all followers
6. WHEN the Inbox receives a Move activity, THE Video Platform SHALL verify the signature matches the original DID
7. WHEN a Move activity is verified, THE Video Platform SHALL update follower records to point to the new instance URL
8. WHEN a User completes migration to a new instance, THE Video Platform SHALL allow export of all Video Posts and metadata in ActivityPub format

### Requirement 9

**User Story:** As an instance operator, I want to implement content moderation capabilities, so that I can maintain community standards and comply with policies.

#### Acceptance Criteria

1. WHEN a Video Post is created, THE Video Platform SHALL scan the video using a content moderation API for policy violations
2. WHEN the moderation API detects explicit content, THE Video Platform SHALL flag the Video Post and prevent it from appearing in public feeds
3. WHEN a Video Post is flagged, THE Video Platform SHALL notify the content creator with the reason for flagging
4. WHEN an instance operator reviews a flagged Video Post, THE Video Platform SHALL provide options to approve, reject, or delete the content
5. WHEN a Video Post is rejected, THE Video Platform SHALL update its status to "rejected" and remove it from all feeds
6. WHEN processing federated content, THE Video Platform SHALL apply the same moderation rules as local content
7. WHEN a federated Video Post violates policies, THE Video Platform SHALL send a Reject activity to the origin instance
8. WHEN the Inbox receives a Delete activity for a Video Post, THE Video Platform SHALL remove the content and all associated data

### Requirement 10

**User Story:** As a developer, I want comprehensive error handling and monitoring, so that I can quickly identify and resolve issues in the video platform.

#### Acceptance Criteria

1. WHEN any API endpoint encounters an error, THE Video Platform SHALL return a structured error response with error code, message, and request ID
2. WHEN a background task fails, THE Video Platform SHALL log the error with full context (task type, parameters, stack trace)
3. WHEN a video processing task fails, THE Video Platform SHALL update the Video Post status and store the error message
4. WHEN federation delivery fails permanently, THE Video Platform SHALL log the failure and mark the remote instance as potentially unreachable
5. WHEN database operations fail, THE Video Platform SHALL implement automatic retry with exponential backoff for transient errors
6. WHEN Redis operations fail, THE Video Platform SHALL fall back to database-backed session storage
7. WHEN Qdrant operations fail, THE Video Platform SHALL fall back to recency-based ranking for feed generation
8. WHEN critical errors occur, THE Video Platform SHALL emit metrics to a monitoring system for alerting
