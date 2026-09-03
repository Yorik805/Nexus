# Nexus Startup Guide

This is the single startup document for the project. Use this as the canonical entry point for running Nexus locally.

Edit [nexus.config.json](nexus.config.json) to change the shared host and ports. Then apply its URLs to the current PowerShell session:

```powershell
cd E:\Nexus
.\scripts\Set-NexusEnvironment.ps1
```

On Linux, use the Bash equivalent:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
```

## Auto-start the voice console on Linux

Run this once on the server after pulling the repository:

```bash
cd ~/Nexus
bash ./scripts/install-voice-console-service.sh
```

This builds the voice console, starts it on port `3001`, enables it at boot, and restarts it if Node exits. Check it with:

```bash
systemctl --user status nexus-voice-console.service
```

The service currently serves HTTP. For tablet microphone access over a remote address, put it behind a trusted HTTPS reverse proxy such as Caddy, or continue using the existing mkcert HTTPS development command when testing manually.

The script also loads private provider variables from the root `.env` when that file exists. Keep `.env` off Git; copy it to another server only through a secure private transfer.

## 1. Start the main Nexus server

```powershell
cd E:\Nexus
python nexus_server.py
```

This starts:
- the Nexus runtime
- the HTTP gateway on the configured host and port
- the realtime WebSocket gateway on the configured host and port

Keep this terminal running.

## 2. Start the dashboard backend

Open a second terminal:

```powershell
cd E:\Nexus
python .\nexus_dashboard_server.py
```

- This serves the dashboard API on the configured host and port
- It reads runtime logs and exposes state to the frontend

## 3. Start the frontend dashboard

Open a third terminal:

```powershell
cd E:\Nexus\nexus-runtime-dashboard
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
python nexus_server.py

# Terminal 2
cd E:\Nexus
python .\nexus_dashboard_server.py

# Terminal 3
cd E:\Nexus\nexus-runtime-dashboard
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
