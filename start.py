#!/usr/bin/env python3
"""
Production startup script for Enhanced Telegram Task Management Bot
Handles deployment-specific requirements and health checks for Cloud Run
"""

import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

# Import the main bot
from main import main as start_bot

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Cloud Run"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_health_server():
    """Start HTTP health check server for deployment"""
    try:
        # Use PORT environment variable or default to 8080
        port = int(os.environ.get('PORT', 8080))
        
        # Create server
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"🌐 Health check server started on port {port}")
        server.serve_forever()
        
    except Exception as e:
        print(f"⚠️ Health server error: {e}")
        # Continue without health server - bot can still work

def check_required_env():
    """Check if required environment variables are set"""
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("🔧 Please set these variables in your deployment configuration")
        sys.exit(1)
    
    return True

def main():
    """Main function for production deployment"""
    print("🚀 Starting Enhanced Telegram Bot for production deployment...")
    print("🌐 Production mode: Autoscale Deployment")
    print("📱 Bot + Website API + Health Check server")
    
    # Check environment variables
    check_required_env()
    
    # Start health check server in a separate thread for Cloud Run
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Start website API in separate thread
    from website_api import app as website_app
    website_thread = threading.Thread(
        target=lambda: website_app.run(host='0.0.0.0', port=8081, debug=False),
        daemon=True
    )
    website_thread.start()
    print("🌐 Website API started on port 8081")
    
    # Small delay to let health server start
    time.sleep(2)
    
    # Start keep-alive service
    from keep_alive import start_keep_alive
    start_keep_alive()
    
    # Start the main bot
    try:
        print("🤖 Starting Telegram bot...")
        start_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Critical bot error: {e}")
        # Keep the container running for debugging
        time.sleep(30)
        sys.exit(1)

if __name__ == "__main__":
    main()