# STT Plugin Architecture

## Hardware Detection

The STT plugin uses a dedicated hardware detector to choose the best execution device.

- `detect_hardware()` performs device selection.
- The system supports `cuda` and `cpu` today.
- When `preferred_device` is `AUTO`, the detector prefers GPU if CUDA is available.
- If GPU is unavailable, the detector falls back to CPU automatically.
- The implementation is designed to support additional accelerators later without changing the public API.

## Automatic Device Selection

The plugin uses a configuration-driven selection strategy:

1. Read `preferred_device` from the STT config.
2. If `preferred_device` is `AUTO`, probe for CUDA.
3. If CUDA is available, select `cuda`.
4. Otherwise, select `cpu`.

No code changes are required to move between devices.

## Model Loading Lifecycle

The model loader is responsible for managing a single STT model instance while Nexus is running.

- `load_model()` loads the model once and caches it.
- `get_loaded_model()` returns the current instance.
- `get_current_device()` returns the selected runtime device.
- `unload_model()` releases the model reference.

The model lifecycle is intentionally simple so future model backends can replace the current model implementation without changing the interface.

## Transcription Flow

The `TRANSCRIBE` action validates audio input, loads the cached model if necessary, and transcribes the file using Faster-Whisper.

- Audio validation ensures the file exists and is a supported format.
- The STT model is not reloaded for every request.
- The returned response includes `text`, `language`, `segments`, `duration`, and `device`.

## Configuration System

The plugin stores default runtime settings in `config.json` and merges them with runtime overrides.

Configuration includes:

- `preferred_device`
- `model_name`
- `compute_type`
- `language`
- `beam_size`
- `vad_enabled`
- `max_audio_length_seconds`
- `sample_rate`

This provides a central place for STT runtime settings and makes the loader reusable across Nexus.
