# Nexus 24/7 Service - Quick Start

## Ports
- `8765`: Nexus HTTP gateway (`http://127.0.0.1:8765`)
- `8766`: Nexus realtime WebSocket gateway (`ws://127.0.0.1:8766/device`)
- `11882`: Python dashboard backend
- `3000`: Next.js dashboard in the browser

## 1. Start Nexus 24/7 (RUNTIME + HTTP GATEWAY)
```powershell
cd E:\Nexus
python nexus_server.py --host 127.0.0.1 --port 8765
```
- Starts Nexus Runtime (event loop, plugins, validators)
- Starts HTTP Gateway on http://127.0.0.1:8765
- Starts realtime WebSocket Gateway on ws://127.0.0.1:8766/device
- Runs 24/7 until Ctrl+C
- Output includes: `Nexus HTTP gateway listening on http://127.0.0.1:8765`
- Keep this terminal running.

## 2. Start the Dashboard Backend
The dashboard backend reads the runtime log and proxies dashboard messages to the
HTTP gateway. Its runtime URL must be `8765`, not the WebSocket port `8766`.

```powershell
# In a separate PowerShell terminal
cd E:\Nexus
$env:NEXUS_DASHBOARD_PORT = "11882"
$env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"
python .\nexus_dashboard_server.py
```
- Keep this terminal running.
- This serves the dashboard API at http://127.0.0.1:11882.

## 3. CLI Client (Optional)
```powershell
cd E:\Nexus
python assets\client\nexus_connection.py 127.0.0.1 8765
```
- The client uses HTTP on `8765` and realtime WebSocket events on `8766`.
- The prompt stays fixed at the bottom while Nexus messages appear above it.

## 4. Next.js Dashboard
```powershell
# In a separate terminal
cd E:\Nexus\nexus-runtime-dashboard
npm install  # first run only
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://127.0.0.1:11882"
npm run dev
```
- Open http://localhost:3000
- Shows event stream, metrics, provider status
- Has terminal input to send messages to Nexus
- Fetches runtime state through the dashboard backend

## 5. Quick Test Workflow
```powershell
# T1: Nexus runtime + HTTP + WebSocket gateways
cd E:\Nexus
python nexus_server.py --host 127.0.0.1 --port 8765

# T2: Dashboard backend
cd E:\Nexus
$env:NEXUS_DASHBOARD_PORT = "11882"
$env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"
python .\nexus_dashboard_server.py

# T3: Next.js dashboard
cd E:\Nexus\nexus-runtime-dashboard
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://127.0.0.1:11882"
npm run dev

# T4: Optional CLI client
cd E:\Nexus
python assets\client\nexus_connection.py 127.0.0.1 8765

# Stop each process with Ctrl+C in its own terminal.
```

## 6. Why This Works
- `nexus_server.py` starts the runtime, HTTP gateway, and realtime WebSocket gateway.
- HTTP gateway handles `POST /message` requests
- WebSocket gateway delivers live device messages
- `nexus_dashboard_server.py` reads logs and proxies dashboard requests to HTTP `8765`
- Next.js proxies `/api/state` and `/api/events` to dashboard backend `11882`

## 7. Dashboard Logs Are Now ACCURATE
The dashboard no longer shows nested JSON like `{"action": "ECHO"}`.
Logs display as: `[timestamp] step key=value key=value`
Fixed in `nexus_dashboard_server.py:33-73`

## 8. Prerequisites for Next.js Dashboard
```powershell
cd E:\Nexus\nexus-runtime-dashboard
npm install  # if not already installed
npm run dev  # starts the dashboard
```