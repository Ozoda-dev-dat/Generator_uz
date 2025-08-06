#!/usr/bin/env python3
"""
Render.com startup script for Enhanced Telegram Task Management Bot
Optimized for Render's free tier hosting
"""

import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Health check endpoint for Render.com"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'service': 'Enhanced Telegram Task Bot',
                'timestamp': time.time(),
                'platform': 'render.com'
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Enhanced Telegram Task Bot</title></head>
            <body>
                <h1>🤖 Enhanced Telegram Task Management Bot</h1>
                <p>✅ Bot is running on Render.com</p>
                <p>📱 Telegram bot is active and ready</p>
                <p>🔗 <a href="/health">Health Check</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging for Render"""
        print(f"[RENDER] {format % args}")

def start_web_server():
    """Start web server for Render.com"""
    try:
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"🌐 Render web server started on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Web server error: {e}")
        sys.exit(1)

def check_environment():
    """Check required environment variables for Render"""
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Set these in Render dashboard under Environment Variables")
        sys.exit(1)
    
    print("✅ All required environment variables are set")

def main():
    """Main function for Render.com deployment"""
    print("🚀 Starting Enhanced Telegram Bot on Render.com...")
    print("🆓 Free tier hosting - optimized for 24/7 operation")
    
    # Check environment
    check_environment()
    
    # Start web server in background thread (required for Render)
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Small delay to let web server start
    time.sleep(2)
    
    # Import and start the bot
    try:
        from main import main as start_bot
        print("🤖 Starting Telegram bot...")
        start_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        # Keep server running for debugging
        time.sleep(60)
        sys.exit(1)

if __name__ == "__main__":
    main()