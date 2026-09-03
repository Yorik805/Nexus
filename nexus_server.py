#!/usr/bin/env python3
"""HTTP gateway for the Nexus runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import websockets

from runtime import (
    NexusRuntime,
    get_device_communication_manager,
    get_device_store,
)
from nexus_config import load_config


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


async def _handle_device_websocket(websocket) -> None:
    manager = get_device_communication_manager()
    store = get_device_store()
    device_id: str | None = None
    try:
        first = await websocket.recv()
        payload = json.loads(first)
        if not isinstance(payload, dict):
            await websocket.send(json.dumps({"status": "ERROR", "message": "device registration payload must be an object."}))
            return

        device_id = str(payload.get("device_id") or "").strip()
        device_type = str(payload.get("device_type") or "websocket").strip()
        if not device_id:
            await websocket.send(json.dumps({"status": "ERROR", "message": "device_id is required."}))
            return

        if not store.get_device(device_id):
            store.register_device(device_id, device_type)
        manager.register_connection(device_id, websocket)
        await websocket.send(json.dumps({"status": "SUCCESS", "type": "CONNECTED", "device_id": device_id}))

        async for raw in websocket:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("type") == "PING":
                await websocket.send(json.dumps({"type": "PONG", "device_id": device_id}))
    except Exception as exc:
        print(f"[NEXUS:ws] Error for device {device_id}: {exc}")
    finally:
        if device_id:
            manager.unregister_connection(device_id)
            try:
                await websocket.close()
            except Exception:
                pass


def start_realtime_device_server(host: str, port: int) -> threading.Thread:
    async def _serve() -> None:
        async with websockets.serve(_handle_device_websocket, host, port):
            await asyncio.Future()

    thread = threading.Thread(target=lambda: asyncio.run(_serve()), daemon=True)
    thread.start()
    return thread


class NexusRequestHandler(BaseHTTPRequestHandler):
    server: NexusHTTPServer

    def _device_event_response(self, device_id: str, event: dict[str, Any]) -> None:
        manager = get_device_communication_manager()
        payload = dict(event)
        payload.setdefault("event_id", str(__import__('uuid').uuid4()))
        payload.setdefault("timestamp", __import__('datetime').datetime.now(__import__('datetime').timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
        payload.setdefault("source", "NEXUS")
        manager.send(device_id, payload)

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
            print(f"[NEXUS:http] Client disconnected during response to {self.path}")
        except Exception as exc:
            print(f"[NEXUS:http] Failed to write response for {self.path}: {exc}")

    def do_POST(self) -> None:
        print(f"[NEXUS:http] {self.command} {self.path} from {self.address_string()}")
        try:
            payload = self._json_body()
            if self.path == "/devices/register":
                print("[NEXUS:http] Handling /devices/register")
                device_id = payload.get("device_id")
                device_type = payload.get("device_type", "unknown")
                if not device_id:
                    print("[NEXUS:http] Missing device_id")
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                print(f"[NEXUS:http] Getting device store...")
                store = get_device_store()
                print(f"[NEXUS:http] Registering device {device_id}...")
                device = store.register_device(device_id, device_type)
                print(f"[NEXUS:http] Device registered: {device}")
                result = {"status": "SUCCESS", "device": device}
                print(f"[NEXUS:http] Writing response...")
                print(f"[NEXUS:http] Response sent for /devices/register")
            elif self.path == "/devices/disconnect":
                device_id = payload.get("device_id")
                if not device_id:
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                store = get_device_store()
                store.unregister_device(device_id)
                result = {"status": "SUCCESS", "message": f"Device {device_id} disconnected."}
                print(f"[NEXUS:http] Response sent for /devices/disconnect")
            elif self.path == "/devices/pending":
                device_id = payload.get("device_id")
                if not device_id:
                    self._write_json(400, {"status": "ERROR", "message": "device_id is required."})
                    return
                store = get_device_store()
                pending = store.get_pending_messages(device_id, consume=True)
                result = {"status": "SUCCESS", "pending": pending, "device_id": device_id}
                print(f"[NEXUS:http] Response sent for /devices/pending")
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
                print(f"[NEXUS:http] Event processed, status={result.get('status')}")
                print(f"[NEXUS:http] Response sent for /message")
                
                # Legacy fallback: if the device is not connected in realtime mode,
                # we still return queued offline messages for compatibility.
                store = get_device_store()
                pending = store.get_pending_messages(device_id, consume=True)
                if pending:
                    result["pending_messages"] = pending
            else:

                self._write_json(404, {"status": "ERROR", "message": "Unknown endpoint."})

                return

            self._write_json(200, result)
        except (ValueError, json.JSONDecodeError) as exc:
            self._write_json(400, {"status": "ERROR", "message": str(exc)})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._write_json(500, {"status": "ERROR", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"HTTP {self.address_string()} - {format % args}")


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=str(config.get("bind_host", "0.0.0.0")))
    parser.add_argument("--port", type=int, default=int(config.get("runtime_port", 8765)))
    parser.add_argument("--realtime-port", type=int, default=int(config.get("realtime_port", 8766)))
    args = parser.parse_args()

    load_dotenv()
    runtime = NexusRuntime()
    runtime.start()
    start_realtime_device_server(args.host, args.realtime_port)
    print(f"Nexus realtime gateway listening on ws://{args.host}:{args.realtime_port}/device")
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
