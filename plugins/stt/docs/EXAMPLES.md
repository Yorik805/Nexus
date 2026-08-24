# STT Plugin Examples

## Install Dependencies

```bash
pip install faster-whisper
```

Make sure `ffmpeg` is installed on the host system.

## Load and Transcribe

```python
from plugins.stt import execute

# Load the model once
load_result = execute({
    "action": "LOAD_MODEL",
    "data": {}
})

if load_result["status"] != "SUCCESS":
    raise RuntimeError(load_result["message"])

# Transcribe a WAV file
response = execute({
    "action": "TRANSCRIBE",
    "data": {
        "audio_path": "/tmp/sample.wav"
    }
})

if response["status"] == "SUCCESS":
    print("Text:", response["data"]["text"])
    print("Language:", response["data"]["language"])
    print("Device:", response["data"]["device"])
else:
    print("Error:", response["message"])
```

## Automatic Device Selection

The plugin uses `preferred_device: AUTO` from `plugins/stt/config.json`.
It will automatically choose `cuda` when available, otherwise `cpu`.

## Model Download

The first time the model loads, Faster-Whisper downloads the model files if needed.
This happens once and the loaded model is reused for subsequent transcriptions.
