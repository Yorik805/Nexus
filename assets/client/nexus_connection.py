"""HTTP boundary between a portable client and the Nexus server."""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from typing import Any


def _transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file to text using faster-whisper if available."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path)
        return " ".join(segment.text for segment in segments).strip()
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Install it with: pip install faster-whisper"
        )
    except Exception as exc:
        raise RuntimeError(f"STT transcription failed: {exc}")


@dataclass
class NexusConnection:
    host: str
    port: int | None = None
    protocol: str = "http"
    timeout: float | None = None

    def __post_init__(self) -> None:
        self.host = self.host.rstrip("/")

    @property
    def base_url(self) -> str:
        port = f":{self.port}" if self.port is not None else ""
        return f"{self.protocol}://{self.host}{port}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        host = self.host
        port = self.port or (443 if self.protocol == "https" else 80)
        try:
            conn = http.client.HTTPConnection(host, port, timeout=self.timeout or 30)
            conn.request(method, path, body=body, headers={"Accept": "application/json", "Content-Type": "application/json"})
            response = conn.getresponse()
            data = response.read().decode("utf-8")
            conn.close()
            if response.status >= 400:
                raise ConnectionError(f"Nexus server returned HTTP {response.status} {response.reason}.")
            result = json.loads(data) if data else {}
        except http.client.HTTPException as exc:
            raise ConnectionError(f"HTTP error from Nexus server: {exc}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ConnectionError(f"Invalid response from Nexus server: {exc}") from exc
        if not isinstance(result, dict):
            raise ConnectionError("Nexus server returned a non-object response.")
        return result

    def register(self, device_id: str, device_type: str) -> dict[str, Any]:
        return self._request("POST", "/devices/register", {"device_id": device_id, "device_type": device_type})

    def send_user_message(self, device_id: str, text: str, message_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"device_id": device_id, "text": text}
        if message_id:
            payload["message_id"] = message_id
        result = self._request("POST", "/message", payload)
        # Return the full result so caller can check for pending_messages
        return result

    def receive_response(self, response: dict[str, Any]) -> str:
        # Check for pending messages from devices.SEND
        pending = response.get("pending_messages", [])
        if pending:
            messages = []
            for msg in pending:
                if isinstance(msg, dict):
                    messages.append(msg.get("message", str(msg)))
                else:
                    messages.append(str(msg))
            # Return pending messages joined with newlines
            text = "\n".join(messages)
            if text.strip():
                return text
        
        # Fallback to response.text
        nested = response.get("response")
        if isinstance(nested, dict):
            response = nested
        text = response.get("text")
        if not isinstance(text, str):
            raise ConnectionError("Nexus response did not contain response.text.")
        return text

    def receive_pending(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/pending", {"device_id": device_id})

    def disconnect(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/disconnect", {"device_id": device_id})


if __name__ == "__main__":
    import sys
    import tempfile
    import os

    def _record_microphone(duration_seconds: int = 5) -> str:
        """Record audio from microphone and return path to temp file."""
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            raise RuntimeError(
                "Microphone recording requires: pip install sounddevice numpy"
            )
        fs = 16000
        print(f"Recording {duration_seconds} seconds of audio...")
        audio = sd.rec(int(duration_seconds * fs), samplerate=fs, channels=1, dtype="float32")
        sd.wait()
        # Normalize and convert to int16 for whisper
        audio_int16 = (audio.flatten() * 32767).astype("int16")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        import wave
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio_int16.tobytes())
        return tmp.name

    def _get_text_via_stt() -> str:
        """Try microphone recording + transcription, fallback to text input."""
        try:
            audio_path = _record_microphone(5)
            print(f"Recorded: {audio_path}")
            text = _transcribe_audio(audio_path)
            os.unlink(audio_path)
            return text
        except RuntimeError as exc:
            print(f"STT unavailable ({exc})")
            return input("Type your message: ").strip()

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    device_id = sys.argv[3] if len(sys.argv) > 3 else "laptop_1"

    conn = NexusConnection(host, port)
    print(conn.register(device_id, "laptop"))

    if "--poll" in sys.argv:
        pending = conn.receive_pending(device_id)
        print("Pending messages:", pending)
        sys.exit(0)

    text = None
    if "--audio" in sys.argv:
        audio_index = sys.argv.index("--audio")
        if audio_index + 1 < len(sys.argv):
            audio_path = sys.argv[audio_index + 1]
            print(f"Transcribing: {audio_path}")
            text = _transcribe_audio(audio_path)
            print(f"Transcribed: {text}")
        else:
            print("Error: --audio requires a file path")
            sys.exit(1)
    elif "--text" in sys.argv:
        text_index = sys.argv.index("--text")
        if text_index + 1 < len(sys.argv):
            text = sys.argv[text_index + 1]
        else:
            print("Error: --text requires a message")
            sys.exit(1)
    else:
        # No args: auto-run STT
        text = _get_text_via_stt()

    if not text:
        print("Error: No text to send")
        sys.exit(1)

    resp = conn.send_user_message(device_id, text)
    pending = resp.get("pending_messages", [])
    if pending:
        print("Pending replies:")
        for msg in pending:
            if isinstance(msg, dict):
                print(f"  - {msg.get('message', msg)}")
            else:
                print(f"  - {msg}")
    else:
        print("Response:", conn.receive_response(resp))
class MockNexusConnection:
    """Offline transport for client tests and microphone/TTS demos."""

    def __init__(self) -> None:
        self.registered: list[tuple[str, str]] = []
        self.messages: list[dict[str, str]] = []

    def register(self, device_id: str, device_type: str) -> dict[str, Any]:
        self.registered.append((device_id, device_type))
        return {"status": "SUCCESS", "device_id": device_id}

    def send_user_message(self, device_id: str, text: str, message_id: str | None = None) -> dict[str, Any]:
        message = {"device_id": device_id, "text": text, "message_id": message_id or "mock-message"}
        self.messages.append(message)
        return {"message_id": "mock-response", "text": f"Mock Nexus response to: {text}"}

    def receive_response(self, response: dict[str, Any]) -> str:
        return str(response["text"])

    def disconnect(self, device_id: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "device_id": device_id}
