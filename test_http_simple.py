import http.client
import json
import time

def test_register():
    print("=== Test 1: POST /devices/register ===")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8765, timeout=10)
        body = json.dumps({"device_id": "laptop_1", "device_type": "laptop"}).encode()
        conn.request("POST", "/devices/register", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        print(f"Status: {response.status}")
        print(f"Reason: {response.reason}")
        data = response.read().decode()
        print(f"Body: {data}")
        conn.close()
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")

def test_message():
    print("\n=== Test 2: POST /message ===")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8765, timeout=30)
        body = json.dumps({"device_id": "laptop_1", "text": "Hello from test"}).encode()
        conn.request("POST", "/message", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        print(f"Status: {response.status}")
        print(f"Reason: {response.reason}")
        data = response.read().decode()
        print(f"Body: {data[:500]}")
        conn.close()
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")

if __name__ == "__main__":
    test_register()
    time.sleep(1)
    test_message()
