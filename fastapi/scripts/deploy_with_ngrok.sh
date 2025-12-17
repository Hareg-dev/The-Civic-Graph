#!/bin/bash
# Deploy FreeWill Video Platform with ngrok

set -e

echo "=========================================="
echo "FreeWill Video Platform - ngrok Deployment"
echo "=========================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed!"
    echo ""
    echo "Install ngrok:"
    echo "  1. Visit: https://ngrok.com/download"
    echo "  2. Download and install ngrok"
    echo "  3. Sign up for free account: https://dashboard.ngrok.com/signup"
    echo "  4. Get your auth token: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "  5. Run: ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo ""
echo "📋 Step 1: Starting local services..."
echo ""

# Start production services
if [ -f "docker-compose.prod.yml" ]; then
    echo "Starting production stack..."
    docker-compose -f docker-compose.prod.yml up -d
else
    echo "Starting development stack..."
    docker-compose up -d
fi

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy (30 seconds)..."
sleep 30

# Check if services are running
echo ""
echo "🏥 Checking service health..."
if curl -f http://localhost/health > /dev/null 2>&1 || curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Services are healthy!"
else
    echo "⚠️  Warning: Services may not be fully ready yet"
    echo "   Continuing anyway..."
fi

# Determine which port to expose
if docker-compose -f docker-compose.prod.yml ps 2>/dev/null | grep -q nginx; then
    PORT=80
    echo ""
    echo "📡 Detected production setup (Nginx on port 80)"
else
    PORT=8000
    echo ""
    echo "📡 Detected development setup (FastAPI on port 8000)"
fi

echo ""
echo "=========================================="
echo "🚀 Starting ngrok tunnel..."
echo "=========================================="
echo ""
echo "Exposing port $PORT to the internet..."
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Keep this terminal window open"
echo "   - ngrok will provide a public URL"
echo "   - Share this URL to test your platform"
echo "   - Free tier has connection limits"
echo ""
echo "Press Ctrl+C to stop ngrok and close the tunnel"
echo ""
echo "=========================================="
echo ""

# Start ngrok
ngrok http $PORT --log=stdout
