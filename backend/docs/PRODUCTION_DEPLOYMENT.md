# Production Deployment Guide

Complete guide for deploying FreeWill Video Platform to production with Gunicorn and Nginx.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Testing](#testing)
7. [Monitoring](#monitoring)
8. [Scaling](#scaling)
9. [Security](#security)
10. [Troubleshooting](#troubleshooting)

## Architecture Overview

```
Internet
    ↓
[Nginx] (Port 80/443)
    ↓ (Reverse Proxy, Load Balancer, SSL Termination)
[Gunicorn] (Multiple Workers)
    ↓
[FastAPI Application]
    ↓
[PostgreSQL] [Redis] [Qdrant]
    ↓
[Celery Workers] (Background Processing)
```

### Components

- **Nginx**: Reverse proxy, load balancer, SSL termination, static file serving
- **Gunicorn**: WSGI HTTP server with multiple worker processes
- **FastAPI**: Application framework
- **PostgreSQL**: Primary database
- **Redis**: Cache and task queue
- **Qdrant**: Vector database for AI features
- **Celery**: Background task processing

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows with Docker
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 100GB+ SSD recommended
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Domain & SSL

- Domain name pointed to your server
- SSL certificate (Let's Encrypt recommended)

## Quick Start

### 1. Clone and Setup

```bash
cd fastapi
```

### 2. Configure Environment

```bash
# Copy production environment template
cp .env.production .env

# Edit with your values
nano .env
```

**Critical values to update:**
- `POSTGRES_PASSWORD`: Strong database password
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `INSTANCE_URL`: Your domain (e.g., https://video.example.com)

### 3. Start Production Services

**Linux/Mac:**
```bash
chmod +x start_production.sh
./start_production.sh
```

**Windows:**
```cmd
start_production.bat
```

### 4. Verify Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Test the deployment
python test_production.py
```

### 5. Access Your Platform

- **Website**: http://localhost (or your domain)
- **API Docs**: http://localhost/docs
- **Health**: http://localhost/health

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
INSTANCE_URL=https://your-domain.com

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=freewill

# Security
SECRET_KEY=your_secret_key_here  # Generate with: openssl rand -hex 32

# Performance
GUNICORN_WORKERS=4  # 2 * CPU_CORES + 1
WORKER_CONCURRENCY=4  # Number of Celery workers

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Gunicorn Configuration

Edit `gunicorn.conf.py`:

```python
# Worker processes (adjust based on CPU cores)
workers = 4  # 2 * CPU_CORES + 1

# Worker class
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5

# Connections
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
```

### Nginx Configuration

Edit `nginx.conf`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Upload size
client_max_body_size 500M;

# Timeouts
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

## Deployment

### Initial Deployment

```bash
# 1. Start services
./start_production.sh

# 2. Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 3. Create admin user (if needed)
docker-compose -f docker-compose.prod.yml exec app python -m app.scripts.create_admin

# 4. Test deployment
python test_production.py
```

### Update Deployment

```bash
# 1. Pull latest code
git pull

# 2. Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 4. Restart workers
docker-compose -f docker-compose.prod.yml restart worker
```

### Zero-Downtime Deployment

```bash
# 1. Build new image
docker-compose -f docker-compose.prod.yml build app

# 2. Scale up with new version
docker-compose -f docker-compose.prod.yml up -d --scale app=2 --no-recreate

# 3. Wait for health checks
sleep 30

# 4. Remove old containers
docker-compose -f docker-compose.prod.yml up -d --scale app=1

# 5. Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## Testing

### Production Load Testing

```bash
# Run comprehensive production tests
python test_production.py
```

Tests include:
- ✅ Health checks
- ✅ Security headers
- ✅ Compression
- ✅ Load testing (100 requests, 10 concurrent users)
- ✅ Rate limiting
- ✅ Concurrent connections

### Manual Testing

```bash
# Health check
curl http://localhost/health

# API documentation
curl http://localhost/docs

# Metrics
curl http://localhost/api/monitoring/metrics

# Load test with Apache Bench
ab -n 1000 -c 10 http://localhost/health
```

### Stress Testing

```bash
# Install wrk
# Ubuntu: sudo apt-get install wrk
# Mac: brew install wrk

# Run stress test
wrk -t12 -c400 -d30s http://localhost/health
```

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f worker

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 app
```

### Health Checks

```bash
# Application health
curl http://localhost/health

# Detailed health
curl http://localhost/api/monitoring/health

# Database health
curl http://localhost/api/monitoring/health/database

# Redis health
curl http://localhost/api/monitoring/health/redis

# Qdrant health
curl http://localhost/api/monitoring/health/qdrant
```

### Metrics

```bash
# Application metrics
curl http://localhost/api/monitoring/metrics

# Nginx metrics
curl http://localhost/nginx_status
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Service resource usage
docker-compose -f docker-compose.prod.yml top
```

## Scaling

### Horizontal Scaling (Multiple App Instances)

Edit `docker-compose.prod.yml`:

```yaml
app:
  deploy:
    replicas: 3  # Run 3 app instances
```

Or scale dynamically:

```bash
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

### Vertical Scaling (More Resources)

Edit `docker-compose.prod.yml`:

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

### Worker Scaling

```bash
# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=4

# Or set in .env
WORKER_CONCURRENCY=8
```

### Database Scaling

For production, consider:
- PostgreSQL replication (master-slave)
- Connection pooling (PgBouncer)
- Read replicas

### Caching Strategy

- Redis for session storage
- Nginx caching for static content
- Application-level caching

## Security

### SSL/TLS Configuration

1. **Get SSL Certificate** (Let's Encrypt):

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com
```

2. **Update nginx.conf**:

Uncomment HTTPS section and update paths:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # ... rest of configuration
}
```

3. **Mount certificates in docker-compose.prod.yml**:

```yaml
nginx:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Security Checklist

- ✅ Strong passwords for database
- ✅ Secure SECRET_KEY
- ✅ SSL/TLS enabled
- ✅ Security headers configured
- ✅ Rate limiting enabled
- ✅ CORS properly configured
- ✅ File upload validation
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ XSS protection
- ✅ CSRF protection

### Firewall Configuration

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to services
sudo ufw deny 5432/tcp  # PostgreSQL
sudo ufw deny 6379/tcp  # Redis
sudo ufw deny 6333/tcp  # Qdrant
sudo ufw deny 8000/tcp  # Gunicorn

# Enable firewall
sudo ufw enable
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### High Memory Usage

```bash
# Check memory usage
docker stats

# Reduce Gunicorn workers
# Edit .env: GUNICORN_WORKERS=2

# Restart
docker-compose -f docker-compose.prod.yml restart app
```

### Slow Response Times

```bash
# Check application logs
docker-compose -f docker-compose.prod.yml logs app

# Check database connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO stats
```

### Database Connection Errors

```bash
# Check PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs postgres

# Check connection string in .env
# Verify DATABASE_URL format

# Test connection
docker-compose -f docker-compose.prod.yml exec app python -c "from app.db import engine; print(engine.connect())"
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose -f docker-compose.prod.yml logs worker

# Check Redis queue
docker-compose -f docker-compose.prod.yml exec redis redis-cli LLEN video_tasks

# Restart worker
docker-compose -f docker-compose.prod.yml restart worker
```

### Nginx 502 Bad Gateway

```bash
# Check if app is running
docker-compose -f docker-compose.prod.yml ps app

# Check app logs
docker-compose -f docker-compose.prod.yml logs app

# Check Nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Restart app
docker-compose -f docker-compose.prod.yml restart app
```

## Performance Tuning

### Gunicorn Optimization

```python
# gunicorn.conf.py
workers = (2 * CPU_CORES) + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

### Nginx Optimization

```nginx
# Worker processes
worker_processes auto;
worker_connections 1024;

# Caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=cache:10m;

# Compression
gzip on;
gzip_types text/plain text/css application/json;
```

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_video_posts_user_id ON video_posts(user_id);
CREATE INDEX idx_video_posts_created_at ON video_posts(created_at);
CREATE INDEX idx_video_posts_status ON video_posts(status);

-- Analyze tables
ANALYZE video_posts;
```

## Backup and Recovery

### Database Backup

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres freewill > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres freewill < backup.sql
```

### File Backup

```bash
# Backup uploads and processed files
tar -czf backup_files.tar.gz uploads/ processed/ federated/

# Restore
tar -xzf backup_files.tar.gz
```

### Automated Backups

Create a cron job:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup_script.sh
```

## Summary

Your production deployment is now ready with:

- ✅ Gunicorn for production-grade WSGI serving
- ✅ Nginx for reverse proxy and load balancing
- ✅ SSL/TLS support
- ✅ Rate limiting and security headers
- ✅ Horizontal and vertical scaling
- ✅ Comprehensive monitoring
- ✅ Load testing capabilities
- ✅ Backup and recovery procedures

For support, check logs and monitoring endpoints first!
