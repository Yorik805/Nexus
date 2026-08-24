from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from plugins.stt.model_loader import get_loaded_model, load_model, unload_model
from plugins.stt.actions.transcribe import transcribe_action


def setup_function() -> None:
    unload_model()


def _create_sample_audio(path: Path) -> None:
    espeak = shutil.which("espeak")
    if not espeak:
        pytest.skip("espeak is required to generate test audio and is not available.")

    subprocess.run(
        [espeak, "-w", str(path), "hello world"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_transcribe_sample_audio_uses_cached_model() -> None:
    pytest.importorskip("faster_whisper")

    sample_audio = Path(__file__).resolve().parent / "sample_audio.wav"
    _create_sample_audio(sample_audio)

    loaded_model = load_model()
    assert loaded_model is not None

    response = transcribe_action({"audio_path": str(sample_audio)})
    assert response["status"] == "SUCCESS", response
    assert isinstance(response["data"], dict)
    assert response["data"].get("text") is not None
    assert response["data"].get("text") != ""
    assert response["data"].get("language") is not None
    assert response["data"].get("device") in {"cpu", "cuda"}

    second_response = transcribe_action({"audio_path": str(sample_audio)})
    assert second_response["status"] == "SUCCESS", second_response
    assert get_loaded_model() is loaded_model

    sample_audio.unlink(missing_ok=True)
