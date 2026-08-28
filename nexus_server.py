#!/usr/bin/env python3
"""HTTP gateway for the Nexus runtime."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from runtime import NexusRuntime, get_device_store, get_device_store


def load_dotenv() -> None:
    """Load local development settings without overwriting the shell."""
    path = os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            if name and name not in os.environ:
                os.environ[name] = value.strip()


class NexusHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], runtime: NexusRuntime) -> None:
        super().__init__(address, NexusRequestHandler)
        self.runtime = runtime


class NexusRequestHandler(BaseHTTPRequestHandler):
    server: NexusHTTPServer

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        try:
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            print("HTTP client disconnected before the response was delivered.")

    def do_POST(self) -> None:
        try:
            payload = self._json_body()
            if self.path == "/devices/register":
                device_id = payload.get("device_id")
                device_type = payload.get("device_type", "unknown")
                if not device_id:
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                store = get_device_store()
                device = store.register_device(device_id, device_type)
                result = {"status": "SUCCESS", "device": device}
            elif self.path == "/devices/disconnect":
                device_id = payload.get("device_id")
                if not device_id:
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                store = get_device_store()
                store.unregister_device(device_id)
                result = {"status": "SUCCESS", "message": f"Device {device_id} disconnected."}
            elif self.path == "/devices/pending":
                device_id = payload.get("device_id")
                if not device_id:
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                store = get_device_store()
                pending = store.get_pending_messages(device_id)
                result = {"status": "SUCCESS", "pending": pending, "device_id": device_id}
            elif self.path == "/message":
                text = payload.get("text")
                device_id = payload.get("device_id", "http-client")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("text must be a non-empty string.")
                
                # Store device if not already known
                store = get_device_store()
                if not store.get_device(device_id):
                    store.register_device(device_id, "http-client")
                
                event = {
                    "type": "USER_MESSAGE",
                    "source": str(device_id),
                    "data": {"text": text},
                }
                print(f"Nexus event received: {event['type']} from {event['source']}")
                result = self.server.runtime.submit_event(event, timeout=None)  # NO TIMEOUT
            else:
                self._write_json(404, {"status": "ERROR", "message": "Unknown endpoint."})
                return
            self._write_json(200, result)
        except (ValueError, json.JSONDecodeError) as exc:
            self._write_json(400, {"status": "ERROR", "message": str(exc)})
        except Exception as exc:
            self._write_json(500, {"status": "ERROR", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"HTTP {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    load_dotenv()
    runtime = NexusRuntime()
    runtime.start()
    server = NexusHTTPServer((args.host, args.port), runtime)
    print(f"Nexus HTTP gateway listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("HTTP gateway shutdown requested.")
    finally:
        server.server_close()
        runtime.stop()


if __name__ == "__main__":
    main()
