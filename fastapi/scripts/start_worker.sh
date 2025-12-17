#!/bin/bash
# Worker startup script for background task processing

set -e

echo "Starting FreeWill Video Platform Worker..."

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

# Start worker
echo "Starting Celery worker..."
celery -A app.workers.tasks worker \
    --loglevel=${LOG_LEVEL:-info} \
    --concurrency=${WORKER_CONCURRENCY:-4} \
    --max-tasks-per-child=1000

