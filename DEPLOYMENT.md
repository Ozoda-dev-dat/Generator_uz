# Deployment Guide for Enhanced Telegram Task Management Bot

## Overview
This guide provides instructions for deploying the Enhanced Telegram Task Management Bot to various cloud platforms, specifically addressing the deployment issues mentioned in the error message.

## Deployment Fixes Applied

### 1. Fixed Run Command Issue
- **Problem**: Deployment failed due to undefined `$file` variable in run command
- **Solution**: Created `start.py` as the main entry point with explicit file specification
- **Implementation**: Production-ready startup script with health checks

### 2. Changed from Autoscale to Background Worker
- **Problem**: Telegram bots don't expose HTTP ports required for Autoscale deployments
- **Solution**: Added HTTP health check server on port 8080 for Cloud Run compatibility
- **Implementation**: Dual-mode operation (Telegram bot + HTTP health endpoint)

### 3. Enhanced Error Handling and Logging
- **Problem**: Limited error diagnostics for startup issues
- **Solution**: Comprehensive error handling with automatic recovery
- **Implementation**: Production-grade logging and restart mechanisms

## Deployment Options

### Option 1: Replit Deployment (Recommended)

#### 🚀 Deploy Commands:
- **Build Command:** bo'sh qoldiring (dependencies avtomatik o'rnatiladi)
- **Start Command:** `python start.py`

#### 🔧 Environment Variables (Replit Secrets):
- `BOT_TOKEN`: Your Telegram bot token (majburiy)
- `ADMIN_CHAT_ID`: 7792775986 (sizning chat ID)
- `ADMIN_CODE`: 1234 (ixtiyoriy)

#### 📋 Deploy qilish bosqichlari:
1. Replit Secrets panelida BOT_TOKEN qo'shing
2. Deploy tugmasini bosing
3. Autoscale Deployment tanlang
4. Start Command: `python start.py`
5. Deploy tugmasini bosing

### Option 2: Cloud Run Deployment
1. Build and push Docker image:
   ```bash
   docker build -t gcr.io/YOUR_PROJECT_ID/telegram-task-bot .
   docker push gcr.io/YOUR_PROJECT_ID/telegram-task-bot
   ```

2. Deploy using gcloud CLI:
   ```bash
   gcloud run deploy telegram-task-bot \
     --image gcr.io/YOUR_PROJECT_ID/telegram-task-bot \
     --platform managed \
     --region us-central1 \
     --set-env-vars ADMIN_CODE=1234,ADMIN_CHAT_ID=7792775986 \
     --set-secrets BOT_TOKEN=bot-token:latest \
     --allow-unauthenticated \
     --min-instances 1 \
     --max-instances 1 \
     --cpu 1 \
     --memory 512Mi \
     --timeout 3600
   ```

3. Or use the provided `deploy.yaml` configuration file

### Option 3: Manual Server Deployment
1. Install dependencies:
   ```bash
   pip install pytelegrambotapi openpyxl trafilatura
   ```

2. Set environment variables:
   ```bash
   export BOT_TOKEN="your_bot_token_here"
   export ADMIN_CODE="1234"
   export ADMIN_CHAT_ID="7792775986"
   ```

3. Run the bot:
   ```bash
   python start.py
   ```

## Configuration Requirements

### Required Environment Variables
- `BOT_TOKEN`: Telegram bot authentication token (required)

### Optional Environment Variables
- `ADMIN_CODE`: Admin verification code (default: "1234")
- `ADMIN_CHAT_ID`: Admin chat ID for notifications (default: 7792775986)
- `PORT`: HTTP server port for health checks (default: 8080)

## Health Check Endpoint
The bot includes an HTTP health check server for deployment platforms that require it:
- **Endpoint**: `http://your-deployment-url/health`
- **Response**: `200 OK` with "Bot is running" message
- **Port**: 8080 (configurable via PORT environment variable)

## Troubleshooting

### Common Issues
1. **Bot Token Error**: Ensure BOT_TOKEN is correctly set in environment variables
2. **Database Initialization**: Bot automatically creates SQLite database on first run
3. **File Permissions**: Ensure write permissions for `reports/` and `media/` directories
4. **Memory Limits**: Recommend at least 512MB RAM for optimal performance

### Log Messages
The bot provides detailed startup logging:
- ✅ Successful initialization messages
- ⚠️ Warning messages for non-critical issues
- ❌ Error messages with specific problem descriptions
- 🔄 Recovery attempt notifications

## Production Considerations

### Security
- Keep BOT_TOKEN secure and never expose in logs
- Use environment variables or secret management systems
- Regularly rotate bot tokens if compromised

### Performance
- Bot uses SQLite database (suitable for small-medium teams)
- Media files stored locally (consider cloud storage for large deployments)
- Automatic polling restart on connection issues

### Monitoring
- Health check endpoint for uptime monitoring
- Detailed console logging for troubleshooting
- Admin notifications for critical events

## Files Modified/Created for Deployment

1. **start.py**: Production startup script with health checks
2. **Dockerfile**: Container configuration for Cloud Run
3. **deploy.yaml**: Cloud Run deployment configuration
4. **DEPLOYMENT.md**: This comprehensive deployment guide
5. **main.py**: Enhanced error handling and logging

These changes ensure the bot can be deployed as either a background worker or with HTTP endpoints as required by different deployment platforms.