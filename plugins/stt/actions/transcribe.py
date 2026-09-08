import os
import wave
from pathlib import Path
from typing import Any

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


def _get_audio_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                return round(wf.getnframes() / float(wf.getframerate()), 2)
        except Exception:
            pass
    return 0.0


def transcribe_audio(audio_path: str, language: str = "en-US") -> dict[str, Any]:
    path = Path(audio_path)
    duration = _get_audio_duration(path)

    # 1. Primary Default STT: Google Speech Recognition (fast, accurate, no heavy local models)
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(path)) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language=language)
        return {
            "text": text.strip(),
            "language": language,
            "duration": duration,
            "engine": "default-google-stt",
        }
    except Exception as sr_err:
        if type(sr_err).__name__ == "UnknownValueError":
            # Audio was silence or unintelligible speech
            return {
                "text": "",
                "language": language,
                "duration": duration,
                "engine": "default-google-stt",
            }

    # 2. Fallback: Gemini Flash via google-genai
    try:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            with open(path, "rb") as f:
                audio_bytes = f.read()
            mime = "audio/wav" if path.suffix.lower() == ".wav" else f"audio/{path.suffix.lstrip('.')}"
            res = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                    "Transcribe this audio verbatim. Output only the spoken words, nothing else. If silence, output nothing.",
                ],
            )
            raw_text = (res.text or "").strip()
            return {
                "text": raw_text,
                "language": language,
                "duration": duration,
                "engine": "gemini-flash-stt",
            }
    except Exception:
        pass

    # 3. Fallback: Local model loader if loaded
    try:
        from ..model_loader import get_loaded_model
        model = get_loaded_model()
        if model is not None:
            return model.transcribe(str(path))
    except Exception:
        pass

    return {
        "text": "",
        "language": language,
        "duration": duration,
        "engine": "default-stt",
    }


def transcribe_action(data: dict) -> dict:
    if not isinstance(data, dict):
        return build_response("ERROR", "TRANSCRIBE requires a dictionary payload.")

    audio_path = data.get("audio_path")
    language = str(data.get("language", "en-US"))
    valid, message, path = _validate_audio_path(audio_path)
    if not valid or path is None:
        return build_response("ERROR", message)

    try:
        result = transcribe_audio(str(path), language=language)
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
