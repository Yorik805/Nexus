# Nexus Quick Start

Use [START_NEXUS.md](START_NEXUS.md) for the complete startup sequence.

The essential dashboard commands are:

```powershell
# Terminal 1: Nexus HTTP + realtime gateways
cd E:\Nexus
python nexus_server.py --host 127.0.0.1 --port 8765

# Terminal 2: dashboard backend
cd E:\Nexus
$env:NEXUS_DASHBOARD_PORT = "11882"
$env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"
python .\nexus_dashboard_server.py

# Terminal 3: Next.js dashboard
cd E:\Nexus\nexus-runtime-dashboard
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://127.0.0.1:11882"
npm run dev
```

Open http://localhost:3000. Do not set `NEXUS_RUNTIME_URL` to `8766`; that port is
the realtime WebSocket gateway, not the dashboard's HTTP backend.

## 3. Use the Nexus Client Connection

### Python Example:

```python
from assets.client.nexus_connection import NexusConnection
from assets.config import load_config
from voice_client import run, make_connection

# Load configuration
config = load_config("assets/config.json")

# Create connection to runtime
conn = make_connection(config)  # Connects to http://100.118.250.51:8765

# Register device
resp = conn.register("laptop_1", "laptop")
print(resp)

# Send a message
resp = conn.send_user_message("laptop_1", "Hello Nexus!")
print("Response:", conn.receive_response(resp))
```

### CLI Example:

```powershell
cd E:\Nexus
python assets\voice_client.py --text "Hello from client"
```