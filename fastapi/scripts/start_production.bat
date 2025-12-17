@echo off
REM Start production deployment with Gunicorn and Nginx

echo ==========================================
echo FreeWill Video Platform - Production Start
echo ==========================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker first.
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found. Creating from .env.production...
    copy .env.production .env
    echo Warning: Please edit .env file with your production values before continuing!
    echo    Especially update:
    echo    - POSTGRES_PASSWORD
    echo    - SECRET_KEY
    echo    - INSTANCE_URL
    pause
)

echo.
echo Configuration loaded from .env file
echo.

REM Stop any existing containers
echo Stopping existing containers...
docker-compose -f docker-compose.prod.yml down

REM Build images
echo Building production images...
docker-compose -f docker-compose.prod.yml build --no-cache

REM Start services
echo Starting production services...
docker-compose -f docker-compose.prod.yml up -d

REM Wait for services to be healthy
echo Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

REM Check service health
echo Checking service health...
docker-compose -f docker-compose.prod.yml ps

REM Run database migrations
echo Running database migrations...
docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head

REM Create necessary directories
echo Creating storage directories...
if not exist uploads mkdir uploads
if not exist processed mkdir processed
if not exist federated mkdir federated
if not exist logs mkdir logs
if not exist logs\nginx mkdir logs\nginx

echo.
echo ==========================================
echo Production deployment started successfully!
echo ==========================================
echo.
echo Services:
echo   Nginx (HTTP):  http://localhost
echo   API Docs:      http://localhost/docs
echo   Health Check:  http://localhost/health
echo   Metrics:       http://localhost/api/monitoring/metrics
echo.
echo Containers:
docker-compose -f docker-compose.prod.yml ps
echo.
echo Useful commands:
echo   View logs:        docker-compose -f docker-compose.prod.yml logs -f
echo   Check status:     docker-compose -f docker-compose.prod.yml ps
echo   Stop services:    docker-compose -f docker-compose.prod.yml down
echo   Restart service:  docker-compose -f docker-compose.prod.yml restart [service]
echo.
echo For HTTPS, configure SSL certificates in nginx.conf and restart nginx
echo.
