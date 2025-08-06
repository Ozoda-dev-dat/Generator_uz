#!/usr/bin/env python3
"""
Keep-alive script to prevent Replit from sleeping
Sends periodic pings to keep the application active
"""

import time
import requests
import threading
from datetime import datetime

def ping_self(port=8080):
    """Send a ping to self to stay awake"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            print(f"💓 {datetime.now().strftime('%H:%M:%S')} - Keep-alive ping successful")
            return True
    except Exception as e:
        print(f"⚠️ {datetime.now().strftime('%H:%M:%S')} - Keep-alive ping failed: {e}")
    return False

def keep_alive_worker():
    """Main keep-alive worker function"""
    print("🚀 Keep-alive service started")
    print("💓 Sending pings every 4 minutes to prevent sleeping")
    
    while True:
        try:
            # Sleep for 4 minutes (240 seconds)
            time.sleep(240)
            
            # Try main health endpoint first
            if not ping_self(8080):
                # Try website API endpoint
                ping_self(8081)
                
        except KeyboardInterrupt:
            print("\n🛑 Keep-alive service stopped")
            break
        except Exception as e:
            print(f"❌ Keep-alive service error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

def start_keep_alive():
    """Start keep-alive service in background thread"""
    keep_alive_thread = threading.Thread(target=keep_alive_worker, daemon=True)
    keep_alive_thread.start()
    return keep_alive_thread

if __name__ == "__main__":
    # Run as standalone script
    keep_alive_worker()