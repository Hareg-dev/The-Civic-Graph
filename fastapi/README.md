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

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker Compose

```bash
docker-compose up -d
```

## Running Workers

Start background workers for video processing:

```bash
celery -A app.workers.tasks worker --loglevel=info
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

Run property-based tests:
```bash
pytest -m property
```

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
