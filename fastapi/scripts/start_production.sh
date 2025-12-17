#!/bin/bash
# Start production deployment with Gunicorn and Nginx

set -e

echo "=========================================="
echo "FreeWill Video Platform - Production Start"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.production..."
    cp .env.production .env
    echo "⚠️  Please edit .env file with your production values before continuing!"
    echo "   Especially update:"
    echo "   - POSTGRES_PASSWORD"
    echo "   - SECRET_KEY"
    echo "   - INSTANCE_URL"
    read -p "Press Enter to continue after updating .env, or Ctrl+C to exit..."
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Validate critical environment variables
if [ "$SECRET_KEY" = "CHANGE_ME_GENERATE_STRONG_SECRET_KEY" ]; then
    echo "❌ Error: Please set a strong SECRET_KEY in .env file"
    exit 1
fi

if [ "$POSTGRES_PASSWORD" = "CHANGE_ME_STRONG_PASSWORD" ]; then
    echo "❌ Error: Please set a strong POSTGRES_PASSWORD in .env file"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "   Environment: $ENVIRONMENT"
echo "   Instance URL: $INSTANCE_URL"
echo "   Gunicorn Workers: ${GUNICORN_WORKERS:-4}"
echo "   Worker Concurrency: ${WORKER_CONCURRENCY:-4}"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Build images
echo "🔨 Building production images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
echo "🚀 Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 15

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.prod.yml ps

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head

# Create necessary directories
echo "📁 Creating storage directories..."
mkdir -p uploads processed federated logs logs/nginx

# Set permissions
echo "🔐 Setting permissions..."
chmod -R 755 uploads processed federated logs

echo ""
echo "=========================================="
echo "✅ Production deployment started successfully!"
echo "=========================================="
echo ""
echo "Services:"
echo "  🌐 Nginx (HTTP):  http://localhost"
echo "  📚 API Docs:      http://localhost/docs"
echo "  ❤️  Health Check: http://localhost/health"
echo "  📊 Metrics:       http://localhost/api/monitoring/metrics"
echo ""
echo "Containers:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "Useful commands:"
echo "  📋 View logs:        docker-compose -f docker-compose.prod.yml logs -f"
echo "  🔍 Check status:     docker-compose -f docker-compose.prod.yml ps"
echo "  🛑 Stop services:    docker-compose -f docker-compose.prod.yml down"
echo "  🔄 Restart service:  docker-compose -f docker-compose.prod.yml restart <service>"
echo ""
echo "⚠️  For HTTPS, configure SSL certificates in nginx.conf and restart nginx"
echo ""
