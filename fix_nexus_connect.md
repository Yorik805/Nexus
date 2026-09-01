# Nexus Connection Fix - The real issue

## Problem: "assets/client/nexus_connect.py dont work"

### Root Cause
The `nexus_connect.py` (actually `assets/client/nexus_connection.py`) works correctly **BUT** only when the Nexus HTTP Gateway is running.

### Two Server Options

#### Option A: `main.py` - Runtime Only
```powershell
cd E:\Nexus
python main.py
```
- Starts ONLY the Nexus Runtime
- NO HTTP gateway on port 8765
- `nexus_connect.py` will FAIL with connection errors
- Use for: background runtime processing

#### Option B: `nexus_server.py` - Runtime + HTTP Gateway ✅
```powershell
cd E:\Nexus
python nexus_server.py
```
- Starts Nexus Runtime
- Starts HTTP Gateway on http://127.0.0.1:8765
- `nexus_connect.py` WORKS correctly
- Use for: 24/7 service with CLI client

### Why the Difference?
- `main.py` (line 22-30): starts `NexusRuntime()` only, no HTTP server
- `nexus_server.py:149-159`: starts `NexusRuntime()` + `NexusHTTPServer()` on port 8765
- The CLI client `voice_client.py` sends `POST /message` to port 8765
- Without the HTTP gateway, requests get 405 Method Not Allowed

### Fixed: Correct Startup Sequence

#### 1. Start Nexus 24/7 (ONE command)
```powershell
cd E:\Nexus
python nexus_server.py
```
Output: `Nexus HTTP gateway listening on http://127.0.0.1:8765`

#### 2. CLI Client (keeps terminal open)
```powershell
cd E:\Nexus
python assets\voice_client.py
```

#### 3. Send a message
```powershell
# In the CLI client terminal:
python assets\voice_client.py --text "Hello Nexus"
```

#### 4. Or use direct HTTP (bypasses CLI)
```powershell
cd E:\Nexus
python -c "
import http.client, json
conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
payload = json.dumps({'device_id': 'test', 'text': 'Hello Nexus'})
conn.request('POST', '/message', body=payload,
             headers={'Content-Type': 'application/json'})
resp = conn.getresponse()
print(f'Status: {resp.status}')
print(f'Response: {resp.read().decode()}')
conn.close()
"
# Output: Status: 200, Response: event received, etc.
```

### The `nexus_connect.py` (assets/client/nexus_connection.py) Code
The code itself is correct. It works when:
- ✅ Server is started with `nexus_server.py`
- ✅ Server is running and listening on port 8765
- ✅ Sending messages via `conn.send_user_message(device_id, text)`

### Don't Use If:
- ❌ Started with `main.py` (runtime only, no HTTP gateway)
✅ Always use `nexus_server.py` for client connectivity

## Summary
The `nexus_connect.py` code is correct. The issue was always starting the wrong server. Use `python nexus_server.py` for 24/7 service with CLI client connections.