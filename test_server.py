#!/usr/bin/env python3
"""Test: Start Nexus server and verify client connection."""

import subprocess
import time
import sys
import os

# Start nexus_server.py in background
print("Starting Nexus server...")
proc = subprocess.Popen(
    [sys.executable, "nexus_server.py"],
    cwd="E:\\Nexus",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(3)

# Check if server started
stdout_val = proc.stdout.read().decode(errors="replace")
stderr_val = proc.stderr.read().decode(errors="replace")
print(f"Server stdout: {stdout_val[-100:]}")
print(f"Server stderr: {stderr_val[-100:]}")

if "listening" in stdout_val.lower():
    print("✓ Server started successfully")
    
    # Try client connection
    print("\nTesting client connection...")
    import time
    time.sleep(1)
    
    # Send a test message using the client approach
    import http.client
    import json
    
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8765, timeout=5)
        payload = json.dumps({"device_id": "test_client", "text": "Hello Nexus"})
        conn.request("POST", "/message", body=payload,
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = response.read().decode()
        print(f"HTTP Response status: {response.status}")
        print(f"HTTP Response data: {data}")
        conn.close()
        
        if response.status == 200:
            print("✓ Client connection successful!")
        elif response.status == 405:
            print("✗ 405 Error - Method Not Allowed")
        elif response.status == 404:
            print("✗ 404 Error - Endpoint not found")
        else:
            print(f"? Unexpected status: {response.status}")
    except Exception as e:
        print(f"✗ Connection error: {e}")
    
    # Stop the server
    print("\nStopping server...")
    proc.terminate()
    proc.wait(timeout=5)
    print("✓ Server stopped")
else:
    print("✗ Server failed to start")
    proc.kill()