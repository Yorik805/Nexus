#!/usr/bin/env python3
"""Dashboard server for Nexus runtime on port 11882."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

DASHBOARD_DIR = Path(__file__).parent / "nexus-runtime-dashboard"
NEXTJS_PORT = 3001
DASHBOARD_PORT = 11882
LOG_PATH = Path(__file__).parent / "logs" / "nexus_runtime.log"
NEXUS_RUNTIME_URL = os.getenv("NEXUS_RUNTIME_URL", "http://127.0.0.1:8765")


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "none"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, sort_keys=True)
    return str(value)


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/state"):
            self._handle_state()
        else:
            self._proxy_to_nextjs()

    def do_POST(self):
        if self.path.startswith("/api/events"):
            self._handle_events()
        else:
            self._proxy_to_nextjs()

    def _proxy_to_nextjs(self):
        try:
            url = f"http://127.0.0.1:{NEXTJS_PORT}{self.path}"
            req = Request(url, method="GET")
            with urlopen(req, timeout=10) as resp:
                body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() in {"content-type", "content-length"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ERROR", "message": str(exc)}).encode())

    def _handle_state(self):
        try:
            events = []
            terminal_lines = []
            iteration = 0
            active_actions = 0
            provider = {"name": "â€”", "model": "â€”", "status": "OFFLINE", "latency": "â€”"}
            uptime = "00:00:00:00"
            progress = 0

            if LOG_PATH.exists():
                raw_lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in raw_lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        terminal_lines.append(line)
                        continue

                    step = entry.get("step", "")
                    details = entry.get("details", {})
                    ts = entry.get("timestamp", "")
                    event_id = entry.get("event_id")

                    events.append({
                        "timestamp": ts,
                        "step": step,
                        "event_id": event_id,
                        "details": details,
                    })

                    kv_pairs = " ".join(f"{k}={_format_value(v)}" for k, v in details.items())
                    terminal_line = f"[{ts}] {step} {kv_pairs}".strip()
                    terminal_lines.append(terminal_line)

                    if step == "iteration.start":
                        iteration = details.get("iteration", iteration)
                    if step == "orchestrator.decision":
                        active_actions = details.get("action_count", 0)
                    if step == "provider.request.start":
                        provider["name"] = details.get("provider", provider["name"])
                        provider["model"] = details.get("model", provider["model"])
                        provider["status"] = "READY"
                    if step == "provider.request.error":
                        provider["status"] = str(details.get("error_code", "ERROR")).upper()
                    if step == "provider.response.received":
                        provider["status"] = "READY"

                events = events[-100:]
                terminal_lines = terminal_lines[-100:]
                progress = min(92, max(0, 46 + active_actions * 11))

            payload = {
                "events": events,
                "terminal_output": "\n".join(terminal_lines),
                "iteration": iteration,
                "activeActions": active_actions,
                "provider": provider,
                "uptime": uptime,
                "progress": progress,
            }
        except Exception as exc:
            payload = {
                "events": [],
                "terminal_output": f"[ERROR] Failed to read state: {exc}",
                "iteration": 0,
                "activeActions": 0,
                "provider": {"name": "ERROR", "model": "â€”", "status": "ERROR"},
                "uptime": "00:00:00:00",
                "progress": 0,
                "error": str(exc),
            }

        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_events(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")

            event_type = payload.get("type", "USER_MESSAGE")
            source = payload.get("source", "dashboard")
            message = payload.get("message", payload.get("text", ""))

            event = {
                "type": event_type,
                "source": source,
                "data": {"text": message} if message else payload.get("data", {}),
            }

            nexus_url = urljoin(NEXUS_RUNTIME_URL, "/message")
            req = Request(nexus_url, data=json.dumps(event).encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            body = json.dumps({"status": "ACCEPTED", "result": result}).encode("utf-8")
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"status": "ERROR", "message": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def main() -> None:
    print(f"Starting Next.js dashboard on port {NEXTJS_PORT}...")
    nextjs_cmd = [
        ("npx.cmd" if sys.platform == "win32" else "npx"), "next", "start",
        "-p", str(NEXTJS_PORT),
        "-H", "127.0.0.1",
    ]
    nextjs_proc = subprocess.Popen(
        nextjs_cmd,
        cwd=str(DASHBOARD_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        for _ in range(60):
            try:
                req = Request(f"http://127.0.0.1:{NEXTJS_PORT}/", method="GET")
                with urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            print("Next.js dashboard failed to start.")
            nextjs_proc.kill()
            sys.exit(1)

        print(f"Next.js dashboard ready on http://127.0.0.1:{NEXTJS_PORT}")

        server = ThreadingHTTPServer(("0.0.0.0", DASHBOARD_PORT), DashboardHandler)
        print(f"Nexus dashboard server listening on http://0.0.0.0:{DASHBOARD_PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server shutdown requested.")
        finally:
            server.server_close()
    finally:
        nextjs_proc.terminate()
        nextjs_proc.wait(timeout=10)


if __name__ == "__main__":
    main()
