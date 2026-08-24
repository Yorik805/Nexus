# Portable Voice Client

This laptop-side client is independent from the Nexus repository, database, plugins, and filesystem. Its only Nexus dependency is the network API.

## Run

From this directory, or after copying `assets` to another machine:

```powershell
python voice_client.py --mock --text "Hello Nexus" --once
python voice_client.py --text "Hello Nexus" --once
python voice_client.py
```

`--mock` runs without a server and returns a simulated response. Normal mode connects to `config.json`. The microphone loop records locally, transcribes locally, sends only text, receives text, and speaks it locally.

## Setup

```powershell
pip install faster-whisper sounddevice pyttsx3
```

Faster-Whisper may download its configured model on first use. Some audio formats require `ffmpeg` on `PATH`.

## Configuration

Edit `config.json` to change the server host, optional port, protocol, timeout, `device_id`, STT model/device preference, TTS, and recording settings. The client never contains a hardcoded server address outside this configuration.

## HTTP contract

Register:

```http
POST /devices/register
Content-Type: application/json
```

```json
{"device_id":"laptop_1","device_type":"laptop"}
```

Send recognized text:

```http
POST /message
Content-Type: application/json
```

```json
{"device_id":"laptop_1","text":"Hello Nexus","message_id":"client-generated-id"}
```

The initial response may be direct or nested:

```json
{"status":"SUCCESS","message_id":"server-message-id","response":{"text":"Hello"}}
```

The client also accepts `{"text":"Hello"}`. Disconnect uses `POST /devices/disconnect` with `{"device_id":"laptop_1"}`. These endpoints are an initial gateway contract and can be extended without coupling the client to the Orchestrator.

## Future clients

Copy this directory and its configuration to another computer. Set a different `device.device_id`, such as `phone_1` or `tablet_1`, and point `server.host` and `server.port` at the gateway. Android, web, and other clients can implement the same text HTTP contract without access to Nexus server files.
