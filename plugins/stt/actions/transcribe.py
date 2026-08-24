from __future__ import annotations

from pathlib import Path
from typing import Any

from ..model_loader import get_loaded_model, load_model
from ..stt_helpers import build_response

_SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".webm",
    ".aac",
    ".mp4",
}


def _validate_audio_path(audio_path: Any) -> tuple[bool, str, Path | None]:
    if not isinstance(audio_path, str) or not audio_path.strip():
        return False, "audio_path must be a non-empty string.", None

    path = Path(audio_path.strip()).expanduser().resolve()
    if not path.exists():
        return False, f"Audio file does not exist: {path}", None
    if not path.is_file():
        return False, f"Audio path is not a file: {path}", None

    if path.suffix.lower() not in _SUPPORTED_AUDIO_EXTENSIONS:
        return (
            False,
            f"Unsupported audio format: {path.suffix}. Supported formats: {', '.join(sorted(_SUPPORTED_AUDIO_EXTENSIONS))}.",
            None,
        )

    return True, "", path


def transcribe_audio(audio_path: str) -> dict[str, Any]:
    model = get_loaded_model()
    if model is None:
        model = load_model()

    return model.transcribe(audio_path)


def transcribe_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "TRANSCRIBE requires a dictionary payload.")

    audio_path = data.get("audio_path")
    valid, message, path = _validate_audio_path(audio_path)
    if not valid:
        return build_response("ERROR", message)

    try:
        result = transcribe_audio(str(path))
    except Exception as exc:  # pragma: no cover
        return build_response(
            "ERROR",
            f"Failed to transcribe audio: {exc}",
        )

    return build_response(
        "SUCCESS",
        "Transcription completed.",
        result,
    )
