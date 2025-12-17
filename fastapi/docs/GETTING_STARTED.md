# Getting Started with FreeWill Video Platform

## Quick Start (5 Minutes)

### Step 1: Start All Services

**Windows:**
```cmd
cd fastapi
start_services.bat
```

**Linux/Mac:**
```bash
cd fastapi
chmod +x start_services.sh
./start_services.sh
```

This will:
- Start PostgreSQL, Redis, and Qdrant in Docker
- Build and start the FastAPI application
- Start background workers
- Run database migrations

### Step 2: Verify Services

```bash
python check_status.py
```

You should see:
```
✓ API: Running
✓ PostgreSQL: Running
✓ Redis: Running
✓ Qdrant: Running
```

### Step 3: Run System Tests

```bash
python test_system.py
```

This will test all platform features with real systems.

### Step 4: Access the Platform

- **API Documentation**: http://localhost:8000/docs
- **API Root**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## What's Running?

After starting services, you'll have:

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI App | 8000 | Main API server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & task queue |
| Qdrant | 6333 | Vector database for AI |
| Celery Worker | - | Background processing |

## Testing the Platform

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. API Documentation
Open http://localhost:8000/docs in your browser to see interactive API documentation.

### 3. Create a User
```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 4. Login
```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

### 5. Check Metrics
```bash
curl http://localhost:8000/api/monitoring/metrics
```

## Viewing Logs

### All Services
```bash
docker-compose logs -f
```

### Specific Service
```bash
docker-compose logs -f app      # Application logs
docker-compose logs -f worker   # Worker logs
docker-compose logs -f postgres # Database logs
```

## Stopping Services

### Stop All Services
```bash
docker-compose down
```

### Stop and Remove All Data
```bash
docker-compose down -v
```

## Troubleshooting

### Services Won't Start

1. **Check Docker is running:**
   ```bash
   docker ps
   ```

2. **Check ports are available:**
   - 8000 (API)
   - 5432 (PostgreSQL)
   - 6379 (Redis)
   - 6333 (Qdrant)

3. **View error logs:**
   ```bash
   docker-compose logs
   ```

### Database Connection Errors

1. **Wait for PostgreSQL to be ready:**
   ```bash
   docker-compose logs postgres
   ```
   Look for "database system is ready to accept connections"

2. **Run migrations manually:**
   ```bash
   docker-compose exec app alembic upgrade head
   ```

### Worker Not Processing Tasks

1. **Check worker logs:**
   ```bash
   docker-compose logs worker
   ```

2. **Restart worker:**
   ```bash
   docker-compose restart worker
   ```

### Port Already in Use

If you get "port already in use" errors:

1. **Find what's using the port:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

2. **Stop the conflicting service or change the port in docker-compose.yml**

## Development Workflow

### 1. Make Code Changes

Edit files in `app/` directory. Changes will be reflected immediately if running in development mode.

### 2. Add Database Changes

```bash
# Create a new migration
docker-compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec app alembic upgrade head
```

### 3. Test Changes

```bash
python test_system.py
```

### 4. Clean Up Development Artifacts

```bash
# Windows
cleanup.bat

# Linux/Mac
./cleanup.sh
```

## Configuration

### Environment Variables

Edit `.env` file to configure:

```bash
# Application
DEBUG=true
ENVIRONMENT=development
INSTANCE_URL=http://localhost:8000

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/freewill

# Redis
REDIS_URL=redis://redis:6379/0

# Qdrant
QDRANT_URL=http://qdrant:6333

# File Limits
MAX_UPLOAD_SIZE_MB=500
MAX_VIDEO_DURATION_SEC=180

# AI Models
VISION_MODEL_NAME=openai/clip-vit-base-patch32
TEXT_MODEL_NAME=all-MiniLM-L6-v2

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Using Ollama for Vision (Optional)

To use Ollama instead of HuggingFace models:

```bash
# In .env
USE_OLLAMA=true
OLLAMA_MODEL=smolvlm
OLLAMA_URL=http://localhost:11434
```

## Platform Features

### 1. Video Upload & Processing
- Upload videos up to 500MB
- Automatic transcoding to multiple resolutions (360p, 480p, 720p, 1080p)
- Thumbnail generation
- Duration limit: 180 seconds

### 2. AI-Powered Recommendations
- Vector similarity search using Qdrant
- Personalized feed based on user interactions
- Cold-start handling for new users

### 3. ActivityPub Federation
- Share content with other federated instances
- Receive federated content
- HTTP Signature verification

### 4. Decentralized Identity (DID)
- Portable user profiles
- Profile migration between instances
- Data export

### 5. Content Moderation
- Automated content scanning (optional)
- Manual moderation interface
- Content flagging and review

### 6. Monitoring & Observability
- Health check endpoints
- Metrics collection
- Structured logging
- Request tracking

## API Endpoints

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /api/monitoring/health` - Detailed health
- `GET /api/monitoring/metrics` - Application metrics

### Users
- `POST /api/users/register` - Register new user
- `POST /api/users/login` - User login
- `GET /api/users/{username}` - Get user profile
- `POST /api/users/migrate` - Migrate profile
- `GET /api/users/export` - Export user data

### Posts
- `POST /api/posts/upload` - Upload video
- `GET /api/posts/{id}` - Get video post
- `GET /api/posts` - List video posts
- `DELETE /api/posts/{id}` - Delete video post

### Feed
- `GET /api/feed` - Get personalized feed
- `GET /api/feed/trending` - Get trending videos

### Interactions
- `POST /api/interactions/like` - Like a video
- `POST /api/interactions/comment` - Comment on video
- `POST /api/interactions/share` - Share a video

### Federation
- `POST /api/federation/inbox` - Receive ActivityPub activities
- `GET /api/federation/outbox` - Get outbox activities

### Moderation
- `POST /api/moderation/scan` - Scan video for violations
- `POST /api/moderation/flag` - Flag content
- `POST /api/moderation/review` - Review flagged content

## Next Steps

1. **Explore the API**: Open http://localhost:8000/docs
2. **Upload a video**: Use the `/api/posts/upload` endpoint
3. **Test federation**: Set up a second instance and test federation
4. **Monitor the system**: Check `/api/monitoring/metrics`
5. **Scale up**: Add more workers or API instances

## Production Deployment

For production deployment, see:
- [README.md](README.md) - Deployment section
- [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md) - Production readiness checklist

## Support

- Check logs: `docker-compose logs -f`
- Run status check: `python check_status.py`
- Run system tests: `python test_system.py`
- View API docs: http://localhost:8000/docs

## Summary

You now have a fully functional federated video platform running locally! 🎉

The platform includes:
- ✅ Video upload and processing
- ✅ AI-powered recommendations
- ✅ ActivityPub federation
- ✅ Decentralized identity
- ✅ Content moderation
- ✅ Comprehensive monitoring

Start building and testing your features!
