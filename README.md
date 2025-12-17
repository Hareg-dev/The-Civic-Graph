# FreeWill Video Platform

A federated short-form video sharing platform with ActivityPub support, AI-powered recommendations, and decentralized identity.

## Features

- **Video Upload & Processing**: Upload videos with automatic transcoding to multiple resolutions
- **AI-Powered Recommendations**: Personalized feed using vector similarity search
- **ActivityPub Federation**: Share and discover content across federated instances
- **Decentralized Identity**: Portable user profiles with DID support
- **Content Moderation**: Automated and manual content moderation tools

## Architecture

```
FastAPI Application
├── API Layer (Routers)
├── Service Layer (Business Logic)
├── Background Workers (Video Processing, AI, Federation)
└── Data Layer (PostgreSQL, Redis, Qdrant)
```

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Qdrant 1.7+
- FFmpeg 5+

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fastapi
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
alembic upgrade head
```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

Using startup script:
```bash
chmod +x start_app.sh
./start_app.sh
```

Or directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis cache
- Qdrant vector database
- FastAPI application
- Background workers

### Running Workers

Start background workers for video processing:

Using startup script:
```bash
chmod +x start_worker.sh
./start_worker.sh
```

Or directly:
```bash
celery -A app.workers.tasks worker --loglevel=info --concurrency=4
```

## Deployment

### Development Deployment

**Quick Start:**
```bash
cd fastapi

# Windows
start_services.bat

# Linux/Mac
chmod +x start_services.sh
./start_services.sh
```

This starts all services (PostgreSQL, Redis, Qdrant, FastAPI, Workers) in development mode.

### Production Deployment with Gunicorn + Nginx

**Complete production setup with load balancing, SSL support, and monitoring.**

**Quick Start:**
```bash
cd fastapi

# 1. Configure environment
cp .env.production .env
nano .env  # Update POSTGRES_PASSWORD, SECRET_KEY, INSTANCE_URL

# 2. Start production services
# Windows
start_production.bat

# Linux/Mac
chmod +x start_production.sh
./start_production.sh

# 3. Test deployment
python test_production.py
```

**What you get:**
- ✅ Nginx reverse proxy with load balancing
- ✅ Gunicorn with multiple workers (4 default)
- ✅ Rate limiting and security headers
- ✅ SSL/TLS ready
- ✅ Horizontal and vertical scaling
- ✅ Health checks and monitoring
- ✅ Automated testing

**Access:**
- Website: http://localhost
- API Docs: http://localhost/docs
- Health: http://localhost/health
- Metrics: http://localhost/api/monitoring/metrics

**See [PRODUCTION_DEPLOYMENT.md](fastapi/PRODUCTION_DEPLOYMENT.md) for complete guide.**

### Docker Deployment

**Development:**
```bash
docker-compose up -d
```

**Production:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Monitoring

Health check endpoints:
- `/health` - Overall health status
- `/api/monitoring/health` - Detailed service health
- `/api/monitoring/health/live` - Liveness probe
- `/api/monitoring/health/ready` - Readiness probe
- `/api/monitoring/metrics` - Application metrics

View logs:
```bash
# Development
docker-compose logs -f

# Production
docker-compose -f docker-compose.prod.yml logs -f
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Quick Start - Real System Testing

**Windows:**
```bash
cd fastapi
start_services.bat
python test_system.py
```

**Linux/Mac:**
```bash
cd fastapi
chmod +x start_services.sh
./start_services.sh
python test_system.py
```

This will:
- ✅ Start all infrastructure services (PostgreSQL, Redis, Qdrant)
- ✅ Run database migrations
- ✅ Start the application and workers
- ✅ Execute comprehensive integration tests
- ✅ Test all features with real systems (no mocks!)

### What Gets Tested

The real system tests validate:
- Infrastructure connectivity (PostgreSQL, Redis, Qdrant)
- System health endpoints
- Database operations
- Redis caching
- Qdrant vector search
- User registration and authentication
- Metrics collection
- Error handling and monitoring

### Manual Testing

```bash
# Start services
docker-compose up -d

# Run system tests
python test_system.py

# Check service health
curl http://localhost:8000/health

# View API documentation
# Open http://localhost:8000/docs in your browser
```

### Debugging & Monitoring

View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f worker
docker-compose logs -f postgres
```

Check service status:
```bash
docker-compose ps
```

Access monitoring endpoints:
- Health: http://localhost:8000/api/monitoring/health
- Metrics: http://localhost:8000/api/monitoring/metrics
- Liveness: http://localhost:8000/api/monitoring/health/live
- Readiness: http://localhost:8000/api/monitoring/health/ready

## Project Structure

```
fastapi/
├── app/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── db.py                # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── redis_client.py      # Redis client
│   ├── ai/
│   │   ├── embeddings.py    # Video embedding generation
│   │   ├── qdrant_client.py # Vector database client
│   │   └── recsys.py        # Recommendation engine
│   ├── federation/
│   │   ├── activitypub.py   # ActivityPub protocol
│   │   ├── inbox.py         # Inbox handler
│   │   └── outbox.py        # Outbox handler
│   ├── workers/
│   │   ├── media.py         # Video processing worker
│   │   └── tasks.py         # Task definitions
│   ├── services/
│   │   ├── upload_manager.py # Upload management
│   │   ├── identity.py       # DID management
│   │   └── moderation.py     # Content moderation
│   └── routers/
│       ├── posts.py         # Post endpoints
│       ├── users.py         # User endpoints
│       ├── feed.py          # Feed endpoints
│       └── federation.py    # Federation endpoints
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `QDRANT_URL`: Qdrant vector database URL
- `INSTANCE_URL`: Public URL of this instance
- `SECRET_KEY`: Secret key for JWT tokens
- `MAX_UPLOAD_SIZE_MB`: Maximum video file size (default: 500MB)
- `MAX_VIDEO_DURATION_SEC`: Maximum video duration (default: 180s)

## Federation

This platform implements ActivityPub for federation with other instances. To federate:

1. Ensure `INSTANCE_URL` is set to your public URL
2. Configure HTTPS (required for federation)
3. Other instances can follow users at: `https://your-instance.com/users/{username}`

## Development

### Adding New Features

1. Create spec in `.kiro/specs/`
2. Implement according to task list
3. Write tests (unit + property-based)
4. Update documentation

### Code Style

```bash
# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

## License

[Your License Here]

## Contributing

[Contributing Guidelines]
