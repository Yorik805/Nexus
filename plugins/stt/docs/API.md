# STT Plugin API

## TRANSCRIBE

Transcribe an existing audio file.

### Request

```json
{
  "action": "TRANSCRIBE",
  "data": {
    "audio_path": "/path/to/audio.wav"
  }
}
```

### Response

Success:

```json
{
  "status": "SUCCESS",
  "message": "Transcription completed.",
  "data": {
    "text": "...",
    "language": "en",
    "segments": [
      {
        "id": 0,
        "start": 0.0,
        "end": 2.1,
        "text": "Hello world."
      }
    ],
    "duration": 2.1,
    "device": "cpu"
  }
}
```

Error:

```json
{
  "status": "ERROR",
  "message": "Audio file does not exist: /path/to/audio.wav",
  "data": {}
}
```

### Notes

- `audio_path` must point to an existing audio file.
- Supported audio formats include WAV, MP3, M4A, FLAC, OGG, WEBM, AAC, and MP4.
- The plugin uses the existing STT model loader and does not reload the model for every request.
- Device selection is automatic and uses CUDA when available.
