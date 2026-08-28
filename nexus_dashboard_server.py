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
            iteration = 0
            active_actions = 0
            provider = {"name": "\u2014", "model": "\u2014", "status": "OFFLINE", "latency": "\u2014"}
            uptime = "00:00:00:00"
            progress = 0

            if LOG_PATH.exists():
                lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    step = entry.get("step", "")
                    details = entry.get("details", {})
                    ts = entry.get("timestamp", "")
                    time_str = ""
                    if ts:
                        try:
                            dt = time.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f%z")
                            ms = ts.split(".")[1].split("+")[0][:3] if "." in ts else "000"
                            time_str = time.strftime("%H:%M:%S", dt) + f".{ms}"
                        except (ValueError, TypeError):
                            time_str = ts.split("T")[-1].split("+")[0] if "T" in ts else ts

                    kind = "SYSTEM"
                    source = str(details.get("source", "runtime"))
                    message = ""
                    response = None

                    if step == "event.received":
                        kind = "USER_MESSAGE"
                        message = f"{details.get('event_type', 'EVENT')} from {source}"
                    elif step == "iteration.start":
                        iteration = details.get("iteration", iteration)
                        message = f"Iteration #{iteration} started"
                    elif step == "context_builder.start" or step == "context_builder.complete":
                        message = f"ContextBuilder {details.get('event_type', '')} \u2014 {details.get('memory_status', '')}"
                    elif step == "provider.request.start":
                        provider["name"] = details.get("provider", provider["name"])
                        provider["model"] = details.get("model", provider["model"])
                        provider["status"] = "READY"
                        message = f"{provider['name']} request started \u00b7 {provider['model']}"
                    elif step == "provider.response.received":
                        text_len = details.get("text_length", 0)
                        message = f"{provider['name']} response received \u00b7 {text_len} chars"
                        response = {
                            "model": provider["model"],
                            "status": 200,
                            "latency": provider.get("latency", "\u2014"),
                            "tokens": str(text_len),
                            "detail": "(response content available in execution history)",
                        }
                    elif step == "provider.request.error":
                        err_code = details.get("error_code", "ERROR")
                        message = f"{provider['name']} error: {err_code}"
                        kind = "ERROR"
                        provider["status"] = err_code.upper()
                    elif step == "orchestrator.decision":
                        active_actions = details.get("action_count", 0)
                        decision = details.get("decision", "CONTINUE")
                        message = f"Decision: {decision} \u00b7 {active_actions} actions"
                    elif step == "validator.complete":
                        approved = details.get("approved_count", 0)
                        message = f"Validator: {approved} actions approved"
                    elif step == "plugin.execution":
                        action = details.get("action", "?")
                        plugin = details.get("plugin", "?")
                        status = details.get("status", "?")
                        kind = "EXECUTION_RESULT"
                        message = f"{plugin}.{action} \u00b7 {status}"
                    elif step == "cycle.complete":
                        message = f"Cycle complete: {details.get('status', '')} / {details.get('termination_reason', '')}"
                    elif step == "event.complete":
                        message = f"Event complete: {details.get('status', '')} / {details.get('termination_reason', '')}"
                    elif step == "provider.request_start":
                        pass

                    if message:
                        events.append({"time": time_str or ts, "kind": kind, "source": source, "message": message, "response": response})

            events = events[-50:]
            progress = min(92, max(0, 46 + active_actions * 11))

            payload = {
                "events": events,
                "iteration": iteration,
                "activeActions": active_actions,
                "provider": provider,
                "uptime": uptime,
                "progress": progress,
            }
        except Exception as exc:
            payload = {"events": [], "iteration": 0, "activeActions": 0, "provider": {"name": "ERROR", "model": "\u2014", "status": "ERROR"}, "uptime": "00:00:00:00", "progress": 0, "error": str(exc)}

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


