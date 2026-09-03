# Nexus Startup Guide

This is the local development startup guide. For the complete Ubuntu server update, auto-start, HTTPS, and recovery workflow, use [SERVER_OPERATIONS.md](SERVER_OPERATIONS.md).

For server updates, restarts, logs, and recovery commands, see [SERVER_OPERATIONS.md](SERVER_OPERATIONS.md).

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

The installer uses `npm` when available, or `pnpm` if that is the package manager installed on the server. If nvm is installed without a shell profile, the installer loads it and installs/uses the Node.js LTS release automatically.
Dependency installation uses retries and a longer registry timeout for slower server connections.

This builds the voice console, starts it on port `3001`, enables it at boot, and restarts it if Node exits. Check it with:

```bash
systemctl --user status nexus-voice-console.service
```

The service currently serves HTTP. For tablet microphone access over a remote address, put it behind a trusted HTTPS reverse proxy such as Caddy, or continue using the existing mkcert HTTPS development command when testing manually.

For the persistent production HTTPS setup, see [SERVER_OPERATIONS.md](SERVER_OPERATIONS.md#enable-https-permanently) and configure Tailscale Serve once with `sudo tailscale serve --bg http://127.0.0.1:3001`.

To make the Python runtime itself use a certificate/key, follow [SERVER_OPERATIONS.md](SERVER_OPERATIONS.md#run-the-python-runtime-with-https-directly).

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
