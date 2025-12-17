# FreeWill Video Platform

A decentralized video platform with ActivityPub federation, AI recommendations, and content moderation.

## Quick Start

### Development
```bash
# Start all services
cd deployment
docker-compose up -d

# Access at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Production
```bash
# Start production stack
cd deployment
docker-compose -f docker-compose.prod.yml up -d

# Access at http://localhost
```

### Deploy to Internet (ngrok)
```bash
# Windows
scripts\setup_ngrok_simple.bat
scripts\deploy_with_ngrok_direct.bat

# Linux/Mac
./scripts/deploy_with_ngrok.sh
```

## Project Structure

```
fastapi/
├── app/              # Application code
│   ├── routers/      # API endpoints
│   ├── services/     # Business logic
│   ├── workers/      # Background tasks
│   ├── ai/           # AI/ML components
│   └── federation/   # ActivityPub
├── deployment/       # Docker & deployment configs
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── nginx.conf
│   └── gunicorn.conf.py
├── scripts/          # Utility scripts
├── tests/            # Test files
├── docs/             # Documentation
└── alembic/          # Database migrations
```

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) - Complete setup guide
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - Production setup
- [ngrok Quick Start](docs/NGROK_QUICK_START.md) - Internet testing

## Testing

```bash
# System tests
python tests/test_system.py

# Production tests
python tests/test_production.py

# ngrok deployment tests
python tests/test_ngrok_deployment.py
```

## Key Features

- 🎥 Video upload and multi-resolution transcoding
- 🤖 AI-powered recommendations
- 🌐 ActivityPub federation
- 🔐 Decentralized identity (DID)
- 🛡️ Content moderation
- 📊 Comprehensive monitoring

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL
- **Cache**: Redis
- **Vector DB**: Qdrant
- **Queue**: Celery
- **Web Server**: Nginx (production)
- **Container**: Docker

## Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

## Health Check

```bash
curl http://localhost:8000/health
```

## Support

- Check service status: `python scripts/check_status.py`
- View logs: `docker-compose logs -f`
- Stop services: `docker-compose down`
