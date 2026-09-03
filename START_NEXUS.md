# Nexus Startup Guide

This is the single startup document for the project. Use this as the canonical entry point for running Nexus locally.

## 1. Start the main Nexus server

```powershell
cd E:\Nexus
python nexus_server.py --host 127.0.0.1 --port 8765
```

This starts:
- the Nexus runtime
- the HTTP gateway on http://127.0.0.1:8765
- the realtime WebSocket gateway on ws://127.0.0.1:8766/device

Keep this terminal running.

## 2. Start the dashboard backend

Open a second terminal:

```powershell
cd E:\Nexus
$env:NEXUS_DASHBOARD_PORT = "11882"
$env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"
python .\nexus_dashboard_server.py
```

- This serves the dashboard API on http://127.0.0.1:11882
- It reads runtime logs and exposes state to the frontend

## 3. Start the frontend dashboard

Open a third terminal:

```powershell
cd E:\Nexus\nexus-runtime-dashboard
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://127.0.0.1:11882"
npm run dev
```

Then open:
- http://localhost:3000

## 4. Optional: run the client

```powershell
cd E:\Nexus
python assets\client\nexus_connection.py 127.0.0.1 8765
```

## 5. Typical full workflow

```powershell
# Terminal 1
cd E:\Nexus
python nexus_server.py --host 127.0.0.1 --port 8765

# Terminal 2
cd E:\Nexus
$env:NEXUS_DASHBOARD_PORT = "11882"
$env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"
python .\nexus_dashboard_server.py

# Terminal 3
cd E:\Nexus\nexus-runtime-dashboard
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://127.0.0.1:11882"
npm run dev
```

## 6. Notes

- `8765` is the HTTP runtime port.
- `8766` is the realtime WebSocket port.
- `11882` is the dashboard backend port.
- `3000` is the browser dashboard port.

## 7. Demo location

The semantic memory demo is now stored under the memory plugin example/test area:
- [plugins/memory/tests/semantic_search_demo.py](plugins/memory/tests/semantic_search_demo.py)
