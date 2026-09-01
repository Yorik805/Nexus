from __future__ import annotations

import asyncio
import json
import sys
import threading
import types
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import websockets

from assets.client.nexus_connection import NexusConnection
from assets.voice_client import SpeechRecognizer, load_config, make_connection
from nexus_server import NexusHTTPServer, _handle_device_websocket
from orchestrators import DummyOrchestrator
from runtime import NexusRuntime


def test_config_is_nested_and_server_is_editable(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"server": {"host": "example.test", "port": 8080}, "device": {"device_id": "phone_1"}}), encoding="utf-8")
    config = load_config(config_path)
    assert config["server"]["host"] == "example.test"
    assert config["server"]["port"] == 8080
    assert config["device"]["device_id"] == "phone_1"


def test_http_connection_sends_device_id_and_text() -> None:
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": {"text": "Hello client"}}).encode())

        def log_message(self, *_args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        connection = NexusConnection("127.0.0.1", server.server_port)
        connection.register("laptop_1", "laptop")
        response = connection.send_user_message("laptop_1", "Hello Nexus")
        assert connection.receive_response(response) == "Hello client"
    finally:
        server.shutdown()
        thread.join()
    assert received[0] == {"device_id": "laptop_1", "device_type": "laptop"}
    assert received[1]["device_id"] == "laptop_1"
    assert received[1]["text"] == "Hello Nexus"


def test_mock_connection_is_available_without_server() -> None:
    connection = make_connection(load_config(Path("assets/config.json")), mock=True)
    connection.register("laptop_1", "laptop")
    response = connection.send_user_message("laptop_1", "test")
    assert connection.receive_response(response) == "Mock Nexus response to: test"


def test_direct_response_is_combined_with_pending_messages() -> None:
    connection = NexusConnection("127.0.0.1", 8765)
    response = {"response": {"text": "Fresh reply"}, "pending_messages": [{"message": "Old reply"}]}
    assert connection.receive_response(response) == "Fresh reply\nOld reply"


def test_pending_response_is_found_at_top_level_when_direct_response_is_empty() -> None:
    connection = NexusConnection("127.0.0.1", 8765)
    response = {"response": {"text": ""}, "pending_messages": [{"message": "Queued reply"}]}
    assert connection.receive_response(response) == "Queued reply"


def test_all_pending_messages_are_returned_in_order_when_direct_response_is_empty() -> None:
    connection = NexusConnection("127.0.0.1", 8765)
    response = {
        "response": {"text": ""},
        "pending_messages": [
            {"message": "First queued reply"},
            {"message": "Second queued reply"},
        ],
    }
    assert connection.receive_response(response) == "First queued reply\nSecond queued reply"


def test_direct_response_and_pending_messages_are_combined() -> None:
    connection = NexusConnection("127.0.0.1", 8765)
    response = {
        "response": {"text": "Main reply"},
        "pending_messages": [
            {"message": "Started task"},
            {"message": "Progress update"},
        ],
    }
    assert connection.receive_response(response) == "Main reply\nStarted task\nProgress update"


def test_generic_failure_text_is_ignored_when_live_pending_messages_exist() -> None:
    connection = NexusConnection("127.0.0.1", 8765)
    response = {
        "response": {"text": "The requested actions have not completed successfully."},
        "pending_messages": [
            {"message": "hi"},
            {"message": "The current time is 1:13:50.53"},
            {"message": "bye"},
        ],
    }
    assert connection.receive_response(response) == "hi\nThe current time is 1:13:50.53\nbye"


def test_send_user_message_can_poll_for_pending_status_updates() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length))
            if self.path == "/message":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": {"text": ""}}).encode())
                return
            if self.path == "/devices/pending":
                assert payload["device_id"] == "laptop_1"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "SUCCESS", "pending": [{"message": "Queued update"}], "device_id": payload["device_id"]}).encode())
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, *_args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        connection = NexusConnection("127.0.0.1", server.server_port)
        response = connection.send_user_message("laptop_1", "hello", poll_pending_seconds=0.2)
        assert connection.receive_response(response) == "Queued update"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_connection_reaches_nexus_runtime_gateway() -> None:
    runtime = NexusRuntime(orchestrator=DummyOrchestrator())
    runtime.start()
    server = NexusHTTPServer(("127.0.0.1", 0), runtime)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        connection = NexusConnection("127.0.0.1", server.server_port)
        connection.register("terminal_b", "test-client")
        response = connection.send_user_message("terminal_b", "Hello through the gateway")
        assert connection.receive_response(response) == "Dummy orchestrator received your message."
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        runtime.stop()


def test_realtime_connection_uses_separate_websocket_port_and_delivers_live_message() -> None:
    runtime = NexusRuntime(orchestrator=DummyOrchestrator())
    runtime.start()
    http_server = NexusHTTPServer(("127.0.0.1", 0), runtime)
    http_thread = threading.Thread(target=http_server.serve_forever)
    http_thread.start()

    async def _serve_realtime() -> None:
        async with websockets.serve(_handle_device_websocket, "127.0.0.1", 0) as ws_server:
            port = ws_server.sockets[0].getsockname()[1]
            connection = NexusConnection("127.0.0.1", http_server.server_port, realtime_port=port)
            connection.register("live_device_1", "test-client")
            assert connection.start_realtime_listener is not None
            assert runtime.device_communication_manager.is_connected("live_device_1")
            response = runtime.device_communication_manager.send("live_device_1", {"type": "MESSAGE", "source": "NEXUS", "data": {"message": "hello-live"}})
            assert response is True

            # Give the live listener a moment to receive the message and verify the connection is active.
            deadline = time.time() + 5
            while time.time() < deadline:
                if connection.get_realtime_events(False):
                    break
                time.sleep(0.05)
            assert connection.get_realtime_events(False)

            await asyncio.sleep(0.2)

    try:
        asyncio.run(_serve_realtime())
    finally:
        http_server.shutdown()
        http_thread.join()
        http_server.server_close()
        runtime.stop()


def test_speech_recognizer_loads_model_once(monkeypatch) -> None:
    instances = []

    class FakeModel:
        def __init__(self, name, device, compute_type):
            instances.append((name, device, compute_type))

        def transcribe(self, path, **kwargs):
            return [types.SimpleNamespace(text="hello")], None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)))
    recognizer = SpeechRecognizer({"model": "small", "device_preference": "AUTO", "compute_type": "float16", "language": "en"})
    assert recognizer.transcribe(Path("sample.wav")) == "hello"
    assert recognizer.transcribe(Path("sample.wav")) == "hello"
    assert instances == [("small", "cpu", "int8")]
