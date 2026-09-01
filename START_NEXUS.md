# Nexus 24/7 Service - Quick Start

## 1. Start Nexus 24/7 (RUNTIME + HTTP GATEWAY)
```powershell
cd E:\Nexus
python nexus_server.py
```
- Starts Nexus Runtime (event loop, plugins, validators)
- Starts HTTP Gateway on http://127.0.0.1:8765
- Runs 24/7 until Ctrl+C
- Output: "Nexus HTTP gateway listening on http://127.0.0.1:8765"

## 2. CLI Client (KEEPS terminal open for sending messages)
```powershell
cd E:\Nexus
python assets\voice_client.py
```
- Terminal stays open for input
- Prompt: "Press Enter to record, or Ctrl+C to quit."
- Send messages: `python assets\voice_client.py --text "Hello Nexus"`
- Nexus replies appear in this terminal

## 3. Next.js Dashboard (BEAUTIFUL UI - the one you made)
```powershell
# In a SEPARATE terminal
cd E:\Nexus\nexus-runtime-dashboard
npm run dev
```
- Opens at http://localhost:3000
- Shows event stream, metrics, provider status
- Has terminal input to send messages to Nexus
- Fetch real logs from the runtime

## 4. Quick Test Workflow
```powershell
# T1: Start Nexus 24/7 (runs until Ctrl+C)
cd E:\Nexus
python nexus_server.py

# T2: Keep this terminal open for CLI client
cd E:\Nexus
python assets\voice_client.py

# T3: In another terminal, start the dashboard
cd E:\Nexus\nexus-runtime-dashboard
npm run dev

# T4: Send messages using CLI client
python assets\voice_client.py --text "Hello Nexus"

# T5: Ctrl+C in T1 to stop everything
```

## 5. Why This Works
- `nexus_server.py:149` starts `NexusRuntime()`
- `nexus_server.py:151` starts `NexusHTTPServer()` on port 8765
- HTTP gateway handles `POST /message` requests
- Client sends messages correctly
- Nexus processes through plugins and can reply via `pending_messages`
- Next.js dashboard fetches state from `/api/state` and events from `/api/events`

## 6. Dashboard Logs Are Now ACCURATE
The dashboard no longer shows nested JSON like `{"action": "ECHO"}`.
Logs display as: `[timestamp] step key=value key=value`
Fixed in `nexus_dashboard_server.py:33-73`

## 7. Prerequisites for Next.js Dashboard
```powershell
cd E:\Nexus\nexus-runtime-dashboard
npm install  # if not already installed
npm run dev  # starts the dashboard
```