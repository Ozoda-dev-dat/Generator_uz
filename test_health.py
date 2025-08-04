#!/usr/bin/env python3
"""
Test script to verify health check server functionality
"""

import threading
import time
import requests
from start import start_health_server

def test_health_check():
    """Test the health check endpoint"""
    # Start health server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    try:
        # Test health endpoint
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200 and 'Bot is running' in response.text:
            print("✅ Health check endpoint working correctly")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check connection failed: {e}")
        return False

if __name__ == "__main__":
    test_health_check()