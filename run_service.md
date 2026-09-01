# Nexus 24/7 Service Setup

## Start Nexus as 24/7 Service

### 1. Start Nexus Runtime + HTTP Gateway
```powershell
cd E:\Nexus
python nexus_server.py
```
Output: `Nexus HTTP gateway listening on http://127.0.0.1:8765`
- This starts the runtime AND the HTTP gateway
- Keeps running until Ctrl+C

### 2. Keep Terminal Open for CLI Client
The CLI client will keep your terminal open and allow sending messages.

### 3. CLI Client - Send & Receive Messages
```powershell
cd E:\Nexus
python assets\voice_client.py
```
-or- with specific server:
```powershell
python assets\voice_client.py --host 127.0.0.1 --port 8765
```

### 4. Using the CLI Client
- Run `python assets\voice_client.py` 
- It will prompt: "Press Enter to record, or Ctrl+C to quit."
- Record audio or type `--text "your message"`
- Nexus processes the message through plugins
- If Nexus replies (via plugins), the response appears
- Type `--text "Hello Nexus"` for quick test

### 5. How Nexus Replies Back
When Nexus processes a message, it checks for pending device messages (`nexus_server.py:98-123`):
- If plugins generate pending messages, they're included in the response
- The CLI client displays these pending messages
- Plugins like `devices.SEND` can send replies back to the device

### 6. Full Startup Sequence
```powershell
# Terminal 1: Start Nexus 24/7
cd E:\Nexus
python nexus_server.py

# Terminal 2: Or keep this terminal open for CLI
cd E:\Nexus
python assets\voice_client.py
```

### 7. Plugin Reply Flow
1. User sends message via CLI: `Hello Nexus`
2. Nexus runtime processes through Validator → PluginRouter
3. If plugin action (e.g., `devices.SEND`), it executes
4. Plugin returns result with status
5. Nexus checks for pending messages (`store.get_pending_messages`)
6. Response includes `pending_messages` array
7. CLI client displays pending messages as replies

### 8. Quick Test
```powershell
# In CLI client
python assets\voice_client.py --text "Hello Nexus"
```

Nexus will process and may reply through its plugins.
```