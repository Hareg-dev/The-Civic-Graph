@echo off
REM Deploy FreeWill Video Platform with ngrok (Direct Path)

echo ==========================================
echo FreeWill Video Platform - ngrok Deployment
echo ==========================================

REM Set ngrok path
set "NGROK_EXE=%USERPROFILE%\ngrok\ngrok.exe"

REM Check if ngrok exists
if not exist "%NGROK_EXE%" (
    echo ngrok is not installed at: %NGROK_EXE%
    echo.
    echo Please run: setup_ngrok_simple.bat
    echo.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

echo.
echo Step 1: Starting local services...
echo.

REM Start production services
if exist docker-compose.prod.yml (
    echo Starting production stack...
    docker-compose -f docker-compose.prod.yml up -d
) else (
    echo Starting development stack...
    docker-compose up -d
)

REM Wait for services to be healthy
echo.
echo Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

REM Check if services are running
echo.
echo Checking service health...
curl -f http://localhost/health >nul 2>&1
if errorlevel 1 (
    curl -f http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        echo Warning: Services may not be fully ready yet
        echo Continuing anyway...
    ) else (
        echo Services are healthy!
    )
) else (
    echo Services are healthy!
)

REM Determine which port to expose
docker-compose -f docker-compose.prod.yml ps 2>nul | findstr nginx >nul
if errorlevel 1 (
    set PORT=8000
    echo.
    echo Detected development setup (FastAPI on port 8000)
) else (
    set PORT=80
    echo.
    echo Detected production setup (Nginx on port 80)
)

echo.
echo ==========================================
echo Starting ngrok tunnel...
echo ==========================================
echo.
echo Exposing port %PORT% to the internet...
echo.
echo IMPORTANT:
echo   - Keep this terminal window open
echo   - ngrok will provide a public URL
echo   - Share this URL to test your platform
echo   - Free tier has connection limits
echo.
echo Press Ctrl+C to stop ngrok and close the tunnel
echo.
echo ==========================================
echo.

REM Start ngrok using direct path
"%NGROK_EXE%" http %PORT%
