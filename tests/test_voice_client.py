from __future__ import annotations

import json
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from assets.client.nexus_connection import NexusConnection
from assets.voice_client import SpeechRecognizer, load_config, make_connection
from nexus_server import NexusHTTPServer
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
