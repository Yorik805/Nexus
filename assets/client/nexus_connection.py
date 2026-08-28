"""HTTP boundary between a portable client and the Nexus server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
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
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ConnectionError(f"Nexus server returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise ConnectionError(f"Could not connect to Nexus server: {exc.reason}") from exc
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
        response = result.get("response")
        if isinstance(response, dict):
            return response
        return result

    def receive_response(self, response: dict[str, Any]) -> str:
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

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    device_id = sys.argv[3] if len(sys.argv) > 3 else "laptop_1"
    
    conn = NexusConnection(host, port)
    print(conn.register(device_id, "laptop"))
    
    # Check for pending messages
    if "--poll" in sys.argv:
        pending = conn.receive_pending(device_id)
        print("Pending messages:", pending)
        sys.exit(0)
    
    # Get text from audio or command line
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
        text = sys.argv[4] if len(sys.argv) > 4 else "Hello from terminal client"
    
    if not text:
        print("Error: No text to send")
        sys.exit(1)
    
    resp = conn.send_user_message(device_id, text)
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
