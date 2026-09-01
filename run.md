# Nexus Quick Start

## 1. Start the Runtime

```powershell
cd E:\Nexus
python main.py
```

## 2. Start the Dashboard Server

```powershell
cd E:\Nexus
set NEXUS_DASHBOARD_PORT=11882
set NEXUS_RUNTIME_URL=http://127.0.0.1:8765
python nexus_dashboard_server.py
```
Open http://0.0.0.0:11882 in your browser.

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