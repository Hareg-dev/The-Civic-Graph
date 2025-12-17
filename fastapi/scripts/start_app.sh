#!/bin/bash
# Application startup script

set -e

echo "Starting FreeWill Video Platform..."

# Wait for services to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${DATABASE_HOST:-localhost} -p ${DATABASE_PORT:-5432} > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready"

echo "Waiting for Redis..."
while ! redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Create necessary directories
mkdir -p uploads processed federated

# Start application
echo "Starting FastAPI application..."
uvicorn app.main:app \
    --host ${HOST:-0.0.0.0} \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-4} \
    --log-level ${LOG_LEVEL:-info}

