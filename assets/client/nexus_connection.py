"""HTTP boundary between a portable client and the Nexus server."""

from __future__ import annotations

import asyncio
import http.client
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

import websockets


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
    realtime_port: int | None = None
    protocol: str = "http"
    timeout: float | None = None
    device_id: str | None = None
    realtime_events: list[dict[str, Any]] | None = None
    _realtime_socket: Any | None = None
    _realtime_thread: threading.Thread | None = None
    _reconnect_attempt: int = 0
    _realtime_connected: threading.Event | None = None
    _realtime_lock: threading.Lock | None = None
    _realtime_stop: threading.Event | None = None

    def __post_init__(self) -> None:
        self.host = self.host.rstrip("/")
        if self.realtime_events is None:
            self.realtime_events = []
        if self._realtime_connected is None:
            self._realtime_connected = threading.Event()
        if self._realtime_lock is None:
            self._realtime_lock = threading.Lock()
        if self._realtime_stop is None:
            self._realtime_stop = threading.Event()
        if self.realtime_port is None and self.port is not None and self.port != 0:
            self.realtime_port = self.port + 1

    def _realtime_url(self) -> str:
        port = self.realtime_port or self.port or 8766
        return f"ws://{self.host}:{port}/device"

    async def _listen_for_realtime_events(self, device_id: str) -> None:
        uri = self._realtime_url()
        attempt = 0
        while not self._realtime_stop.is_set():
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                    attempt = 0
                    self._reconnect_attempt = 0
                    await websocket.send(json.dumps({"device_id": device_id, "device_type": "client"}))
                    async for payload in websocket:
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(event, dict):
                            if event.get("type") == "CONNECTED":
                                self._realtime_connected.set()
                            with self._realtime_lock:
                                self.realtime_events.append(event)
            except Exception:
                self._realtime_connected.clear()
                attempt += 1
                self._reconnect_attempt = attempt
                delay = min(1.0 * (2 ** (attempt - 1)), 10.0)
                self._realtime_stop.wait(delay)

    def start_realtime_listener(self, device_id: str) -> None:
        self.device_id = device_id
        self._realtime_stop.clear()
        if self._realtime_thread is not None and self._realtime_thread.is_alive():
            return
        self._realtime_thread = threading.Thread(target=lambda: asyncio.run(self._listen_for_realtime_events(device_id)), daemon=True)
        self._realtime_thread.start()

    def get_realtime_events(self, clear: bool = True) -> list[dict[str, Any]]:
        if self.realtime_events is None:
            return []
        with self._realtime_lock:
            events = list(self.realtime_events)
            if clear:
                self.realtime_events.clear()
        return events

    def wait_for_realtime_connection(self, timeout: float = 5.0) -> bool:
        """Wait until the device registration handshake succeeds."""
        return self._realtime_connected.wait(timeout)

    def wait_for_realtime_messages(self, timeout: float = 2.0) -> list[dict[str, Any]]:
        """Collect messages already sent for this device without using offline polling."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            events = self.get_realtime_events()
            if any(event.get("type") == "MESSAGE" for event in events):
                return events
            time.sleep(0.05)
        return self.get_realtime_events()

    @property
    def base_url(self) -> str:
        port = f":{self.port}" if self.port is not None else ""
        return f"{self.protocol}://{self.host}{port}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        host = self.host
        port = self.port or (443 if self.protocol == "https" else 80)
        try:
            conn = http.client.HTTPConnection(host, port, timeout=self.timeout)
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
        result = self._request("POST", "/devices/register", {"device_id": device_id, "device_type": device_type})
        self.start_realtime_listener(device_id)
        self.wait_for_realtime_connection()
        return result

    def send_user_message(
        self,
        device_id: str,
        text: str,
        message_id: str | None = None,
        poll_pending_seconds: float | None = 0.2,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"device_id": device_id, "text": text}
        if message_id:
            payload["message_id"] = message_id
        result = self._request("POST", "/message", payload)

        if not self._realtime_connected.is_set() and poll_pending_seconds is not None and poll_pending_seconds > 0:
            try:
                pending = self.receive_pending(device_id)
                if pending.get("status") == "SUCCESS" and isinstance(pending.get("pending", []), list):
                    if not isinstance(result.get("pending_messages"), list):
                        result["pending_messages"] = pending["pending"]
            except ConnectionError:
                pass

        # Return the full result so caller can check for pending_messages
        return result

    def receive_response(self, response: dict[str, Any]) -> str:
        generic_failure_text = "The requested actions have not completed successfully."
        parts: list[str] = []

        nested = response.get("response")
        if isinstance(nested, dict):
            text = nested.get("text")
            if isinstance(text, str) and text.strip():
                candidate = text.strip()
                if candidate != generic_failure_text:
                    parts.append(candidate)

        pending = response.get("pending_messages", [])
        if isinstance(pending, list) and pending:
            for item in pending:
                if isinstance(item, dict):
                    message = item.get("message")
                    if isinstance(message, str) and message.strip() and message.strip() != generic_failure_text:
                        parts.append(message.strip())
                elif isinstance(item, str) and item.strip() and item.strip() != generic_failure_text:
                    parts.append(item.strip())

        if parts:
            return "\n".join(parts)

        raise ConnectionError("Nexus response did not contain response.text and no fresh pending device messages were available.")

    def receive_pending(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/pending", {"device_id": device_id})

    def disconnect(self, device_id: str) -> dict[str, Any]:
        result = self._request("POST", "/devices/disconnect", {"device_id": device_id})
        self._realtime_stop.set()
        self._realtime_connected.clear()
        return result


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
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.patch_stdout import patch_stdout
        except ImportError:
            PromptSession = None
            patch_stdout = None

        def print_live_events() -> None:
            while not conn._realtime_stop.is_set():
                events = conn.get_realtime_events()
                for event in events:
                    if event.get("type") != "MESSAGE":
                        continue
                    data = event.get("data")
                    message = data.get("message") if isinstance(data, dict) else None
                    if isinstance(message, str) and message.strip():
                        print(f"Nexus> {message.strip()}")
                time.sleep(0.05)

        event_thread = threading.Thread(target=print_live_events, name="nexus-cli-events", daemon=True)
        event_thread.start()
        print(f"Connected to Nexus at {conn.base_url}. Type messages; use /quit to exit.")
        try:
            prompt_session = PromptSession("You> ") if PromptSession else None
            stdout_context = patch_stdout(raw=True) if patch_stdout else None
            if stdout_context:
                stdout_context.__enter__()
            try:
                while True:
                    text = (prompt_session.prompt() if prompt_session else input("You> ")).strip()
                    if text.lower() in {"/quit", "/exit"}:
                        break
                    if not text:
                        continue
                    response = conn.send_user_message(device_id, text)
                    if not conn._realtime_connected.is_set():
                        try:
                            print(f"Nexus> {conn.receive_response(response)}")
                        except ConnectionError as exc:
                            print(f"Nexus error: {exc}")
            finally:
                if stdout_context:
                    stdout_context.__exit__(None, None, None)
        except (EOFError, KeyboardInterrupt):
            print()
        finally:
            conn.disconnect(device_id)
        sys.exit(0)

    if not text:
        print("Error: No text to send")
        sys.exit(1)

    resp = conn.send_user_message(device_id, text)
    print("Response:", conn.receive_response(resp))
    conn.disconnect(device_id)
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
