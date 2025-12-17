#!/bin/bash
# Start all services for the FreeWill Video Platform

echo "Starting FreeWill Video Platform services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose down

# Build and start services
echo "Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo "Checking service health..."
docker-compose ps

# Run database migrations
echo "Running database migrations..."
docker-compose exec -T app alembic upgrade head

echo ""
echo "✓ All services started successfully!"
echo ""
echo "Services:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Qdrant: http://localhost:6333"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
