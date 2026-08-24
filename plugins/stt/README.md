# Nexus STT Plugin

The Nexus Speech-to-Text (STT) Plugin v1 provides hardware detection, device selection, model loading, and transcription for existing audio files.

## Purpose

This plugin is the Nexus foundation for speech transcription. It chooses the best available device automatically, keeps the model resident in memory, and returns structured transcription results.

## What is implemented

- Hardware detection for CUDA-enabled NVIDIA GPUs and CPU fallback
- Automatic device selection using `AUTO` preference
- A reusable model loader that loads once and reuses the instance
- Transcription using `faster-whisper`
- Validation for audio file paths and supported formats
- Graceful error handling in the plugin execute API
- Plugin actions for loading, transcribing, querying, and unloading the model

## Dependencies

Install the STT runtime dependencies with:

```bash
pip install faster-whisper
```

Faster-Whisper also requires `ffmpeg` to decode many audio formats.

## Configuration

The plugin reads configuration from `config.json` by default.

Default values:

- `preferred_device`: `AUTO`
- `model_name`: `nexus/stt-base`
- `compute_type`: `float16`
- `language`: `en`
- `beam_size`: `5`
- `vad_enabled`: `false`
- `max_audio_length_seconds`: `30`
- `sample_rate`: `16000`

`AUTO` means: use GPU if available, otherwise CPU.

## Public Functions

The STT foundation exposes the following internal functions:

- `detect_hardware()`
- `load_model()`
- `get_loaded_model()`
- `get_current_device()`
- `unload_model()`

## Plugin Actions

Supported plugin actions:

- `DETECT_HARDWARE`
- `LOAD_MODEL`
- `TRANSCRIBE`
- `GET_MODEL`
- `GET_DEVICE`
- `UNLOAD_MODEL`

## Transcription API

```python
from plugins.stt import execute

request = {
    "action": "TRANSCRIBE",
    "data": {
        "audio_path": "/path/to/audio.wav"
    }
}

response = execute(request)
if response["status"] == "SUCCESS":
    print(response["data"]["text"])
else:
    print("Error:", response["message"])
```

## Notes

- Model loading is cached. The STT model is loaded once and reused across transcription requests.
- GPU execution is used automatically when CUDA is available.
- If CPU is selected and `compute_type` is `float16`, the plugin will fallback to `float32`.
