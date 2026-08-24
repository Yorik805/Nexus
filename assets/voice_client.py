"""Portable laptop voice client for the Nexus HTTP API."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
import wave
from pathlib import Path
from threading import Thread
from typing import Any

try:
    from .client.nexus_connection import MockNexusConnection, NexusConnection
except ImportError:
    from client.nexus_connection import MockNexusConnection, NexusConnection

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {"host": "", "port": None, "protocol": "http", "timeout_seconds": 30},
    "device": {"device_id": "laptop_1", "device_type": "laptop"},
    "stt": {"enabled": True, "model": "small", "device_preference": "AUTO", "compute_type": "float16", "language": "en"},
    "tts": {"enabled": True, "rate": 175, "volume": 1.0},
    "recording": {"microphone_device": None, "sample_rate": 16000, "recording_seconds": 30, "silence_timeout_seconds": 1.2, "silence_threshold": 0.01},
}


def load_config(path: str | Path) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    with Path(path).open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("Client configuration must be a JSON object.")
    for section, values in loaded.items():
        if isinstance(values, dict) and isinstance(config.get(section), dict):
            config[section].update(values)
    return config


class SpeechRecognizer:
    """Local, replaceable faster-whisper adapter with one cached model."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._model = None

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("STT requires faster-whisper.") from exc
        preference = str(self.config.get("device_preference", "AUTO")).upper()
        device = "cpu"
        if preference in {"AUTO", "CUDA"}:
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
            except (ImportError, OSError):
                pass
        compute_type = str(self.config.get("compute_type", "float16"))
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"
        self._model = WhisperModel(str(self.config.get("model", "small")), device=device, compute_type=compute_type)
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        segments, _ = self._ensure_model().transcribe(str(audio_path), language=str(self.config.get("language", "en")), vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()


class MicrophoneRecorder:
    """Local microphone adapter; no audio is sent to the server."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def record(self) -> Path:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Microphone mode requires numpy and sounddevice.") from exc
        sample_rate = int(self.config["sample_rate"])
        audio = sd.rec(int(float(self.config["recording_seconds"]) * sample_rate), samplerate=sample_rate, channels=1, dtype="float32", device=self.config.get("microphone_device"))
        sd.wait()
        samples = audio[:, 0]
        active = np.flatnonzero(np.abs(samples) >= float(self.config["silence_threshold"]))
        if active.size:
            end = int(active[-1]) + int(float(self.config["silence_timeout_seconds"]) * sample_rate)
            samples = samples[:min(end, len(samples))]
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_path = Path(handle.name)
        handle.close()
        pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
        with wave.open(str(output_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(pcm.tobytes())
        return output_path


class TextToSpeech:
    """Local, replaceable TTS adapter with one reusable engine."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.enabled = bool(config.get("enabled", True))
        self._engine = None
        if self.enabled:
            try:
                import pyttsx3
            except ImportError as exc:
                raise RuntimeError("TTS requires pyttsx3, or disable tts.enabled.") from exc
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", int(config.get("rate", 175)))
            self._engine.setProperty("volume", float(config.get("volume", 1.0)))

    def speak(self, text: str) -> None:
        if self.enabled and text:
            assert self._engine is not None
            self._engine.say(text)
            self._engine.runAndWait()

    def speak_async(self, text: str) -> Thread | None:
        if not self.enabled or not text:
            return None
        thread = Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread


def make_connection(config: dict[str, Any], mock: bool = False) -> Any:
    if mock:
        return MockNexusConnection()
    server = config["server"]
    return NexusConnection(server["host"], server.get("port"), server.get("protocol", "http"), float(server.get("timeout_seconds", 30)))


def run(config: dict[str, Any], connection: Any, text: str | None = None, once: bool = False) -> None:
    device = config["device"]
    device_id = str(device["device_id"])
    connection.register(device_id, str(device.get("device_type", "unknown")))
    recognizer = SpeechRecognizer(config["stt"]) if config["stt"].get("enabled", True) else None
    recorder = MicrophoneRecorder(config["recording"])
    tts = TextToSpeech(config["tts"])
    try:
        while True:
            input_text = text
            if input_text is None:
                input("Press Enter to record, or Ctrl+C to quit. ")
                recording_path = recorder.record()
                try:
                    if recognizer is None:
                        raise RuntimeError("STT is disabled, so microphone mode cannot transcribe audio.")
                    input_text = recognizer.transcribe(recording_path)
                finally:
                    recording_path.unlink(missing_ok=True)
            if input_text and input_text.strip():
                response = connection.send_user_message(device_id, input_text.strip())
                response_text = connection.receive_response(response)
                thread = tts.speak_async(response_text)
                if thread is not None:
                    thread.join()
            if once:
                return
            text = None
    finally:
        connection.disconnect(device_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--text", help="Send text without using the microphone.")
    parser.add_argument("--mock", action="store_true", help="Use an offline mock Nexus response.")
    parser.add_argument("--once", action="store_true", help="Process one interaction and exit.")
    args = parser.parse_args()
    config = load_config(args.config)
    run(config, make_connection(config, args.mock), args.text, args.once)


if __name__ == "__main__":
    main()
