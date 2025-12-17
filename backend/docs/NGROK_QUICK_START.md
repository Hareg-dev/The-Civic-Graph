# ngrok Quick Start Guide

## Installation ✅

ngrok is successfully installed at: `C:\Users\DABC\ngrok\ngrok.exe`

## Quick Start (Windows)

### 1. Install ngrok (if not already installed)

```cmd
.\setup_ngrok_simple.bat
```

### 2. Verify Installation

```cmd
.\verify_ngrok.bat
```

### 3. Deploy Your Platform

```cmd
.\deploy_with_ngrok_direct.bat
```

This will:
- ✅ Start all services (PostgreSQL, Redis, Qdrant, App, Workers)
- ✅ Wait for services to be healthy
- ✅ Start ngrok tunnel
- ✅ Display your public URL (e.g., `https://abc123.ngrok.io`)

### 4. Test Your Deployment

```cmd
python test_ngrok_deployment.py
```

## What You'll See

When ngrok starts, you'll see output like:

```
ngrok

Session Status                online
Account                       your-email@example.com
Forwarding                    https://abc123.ngrok.io -> http://localhost:80

Web Interface                 http://127.0.0.1:4040
```

Your public URL is: **https://abc123.ngrok.io**

## Access Your Platform

Once deployed, you can access:

- **Website**: https://your-ngrok-url.ngrok.io
- **API Docs**: https://your-ngrok-url.ngrok.io/docs
- **Health Check**: https://your-ngrok-url.ngrok.io/health
- **Metrics**: https://your-ngrok-url.ngrok.io/api/monitoring/metrics
- **ngrok Dashboard**: http://localhost:4040 (inspect requests/responses)

## Manual ngrok Usage

If you want to run ngrok manually:

```cmd
# Development (FastAPI on port 8000)
C:\Users\DABC\ngrok\ngrok.exe http 8000

# Production (Nginx on port 80)
C:\Users\DABC\ngrok\ngrok.exe http 80
```

## Troubleshooting

### "ngrok not found" error

Use the direct deployment script:
```cmd
.\deploy_with_ngrok_direct.bat
```

### Re-install ngrok

```cmd
.\setup_ngrok_simple.bat
```

### Check ngrok version

```cmd
C:\Users\DABC\ngrok\ngrok.exe version
```

### View ngrok configuration

```cmd
C:\Users\DABC\ngrok\ngrok.exe config check
```

### Services not starting

```cmd
# Check Docker is running
docker info

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Connection refused

```bash
# Restart services
docker-compose restart

# Or restart everything
docker-compose down
.\deploy_with_ngrok_direct.bat
```

## Use Cases

### 1. Development Testing
Test from different devices and networks using the ngrok URL

### 2. Client Demos
Share the ngrok URL with clients or stakeholders for instant access

### 3. Webhook Testing
Configure external services to send webhooks to your ngrok URL

### 4. Mobile App Testing
Point your mobile app to the ngrok URL to test API calls

## Important Notes

### Free Tier Includes:
- ✅ HTTPS support
- ✅ Request inspection at http://localhost:4040
- ✅ 40 connections/minute
- ✅ 1 online ngrok process

### Limitations:
- ⚠️ URL changes each restart (unless paid plan)
- ⚠️ Connection limits on free tier
- ⚠️ Session timeout after 8 hours
- ⚠️ **Not suitable for production**

### Security Notes:
- 🔒 ngrok is for testing/demo only
- 🔒 Your local server is exposed to the internet
- 🔒 Monitor the ngrok dashboard for suspicious activity
- 🔒 Stop ngrok when not needed (Ctrl+C)

## Stopping ngrok

### Stop ngrok Tunnel
Press `Ctrl+C` in the terminal where ngrok is running

### Stop All Services
```cmd
docker-compose down
```

## Advanced Configuration

### Custom Subdomain (Paid Plan)
```cmd
C:\Users\DABC\ngrok\ngrok.exe http 80 --subdomain=myapp
```

### Basic Authentication
```cmd
C:\Users\DABC\ngrok\ngrok.exe http 80 --auth="username:password"
```

### Custom Region
```cmd
C:\Users\DABC\ngrok\ngrok.exe http 80 --region=eu  # Europe
C:\Users\DABC\ngrok\ngrok.exe http 80 --region=ap  # Asia Pacific
```

## For Production Deployment

ngrok is great for testing, but for production use:
- **Cloud Providers**: AWS, Google Cloud, Azure
- **Platform as a Service**: Heroku, Railway, Render
- **VPS**: DigitalOcean, Linode, Vultr

See `PRODUCTION_DEPLOYMENT.md` for production deployment guide.

## Support

- **ngrok Documentation**: https://ngrok.com/docs
- **ngrok Dashboard**: https://dashboard.ngrok.com
- **Local Dashboard**: http://localhost:4040
- **Platform Health**: https://your-url.ngrok.io/health

Happy testing! 🚀
