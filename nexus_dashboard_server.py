#!/usr/bin/env python3
"""Pure-Python terminal dashboard server for Nexus runtime."""

from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from nexus_config import config_value, host_url

DASHBOARD_PORT = int(os.getenv("NEXUS_DASHBOARD_PORT", str(config_value("dashboard_port", 11882))))
LOG_PATH = Path(__file__).parent / "logs" / "nexus_runtime.log"
NEXUS_RUNTIME_URL = os.getenv("NEXUS_RUNTIME_URL", f"http://127.0.0.1:{config_value('runtime_port', 8765)}")


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


def _format_kv_pair(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "none"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, sort_keys=True)
    return str(value)


def _flatten_details(details: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for k, v in details.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                parts.append(f"{sub_k}={_format_kv_pair(sub_v)}")
        elif isinstance(v, list):
            parts.append(f"{k}={_format_kv_pair(v)}")
        else:
            parts.append(f"{k}={_format_kv_pair(v)}")
    return parts


def _read_terminal_lines(limit: int = 200) -> list[str]:
    lines: list[str] = []
    if not LOG_PATH.exists():
        return lines
    try:
        raw_lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                lines.append(line)
                continue
            step = entry.get("step", "")
            details = entry.get("details", {})
            ts = entry.get("timestamp", "")
            kv_pairs = " ".join(_flatten_details(details)) if details else ""
            formatted = f"[{ts}] {step} {kv_pairs}".strip()
            lines.append(formatted)
    except Exception:
        lines.append("[ERROR] Failed to read log file.")
    return lines[-limit:]


def _read_runtime_entries(limit: int = 200) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _build_dashboard_state() -> dict[str, Any]:
    entries = _read_runtime_entries()
    events: list[dict[str, Any]] = []
    provider = {"name": "-", "model": "-", "status": "OFFLINE"}
    iteration = 0
    active_actions = 0
    progress = 0
    for entry in entries:
        step = str(entry.get("step", ""))
        details = entry.get("details", {}) if isinstance(entry.get("details", {}), dict) else {}
        timestamp = str(entry.get("timestamp", ""))
        time_text = timestamp[11:19] if len(timestamp) >= 19 else timestamp
        if step == "iteration.start":
            iteration = int(details.get("iteration", iteration) or iteration)
        if step == "orchestrator.decision":
            active_actions = int(details.get("action_count", 0) or 0)
            progress = 100 if details.get("complete") else min(95, max(0, active_actions * 20))
        if step == "provider.request.start":
            provider = {"name": str(details.get("provider", "-")), "model": str(details.get("model", "-")), "status": "ONLINE"}
        if step == "provider.request.error":
            provider["status"] = "ERROR"
        if step in {"event.received", "provider.response.parsed", "provider.request.error", "plugin.execution", "event.complete"}:
            if step == "event.received":
                kind, source, message = "USER_MESSAGE", str(details.get("source", "runtime")), "Event received"
            elif step == "provider.request.error":
                kind, source, message = "ERROR", str(details.get("provider", "provider")), str(details.get("error_code", "Provider error"))
            elif step == "plugin.execution":
                kind, source, message = "EXECUTION_RESULT", str(details.get("plugin", "plugin")), f"{details.get('action', 'action')} {details.get('status', '')}".strip()
            elif step == "provider.response.parsed":
                kind, source, message = "SYSTEM", str(details.get("provider", "provider")), "Structured response parsed"
            else:
                kind, source, message = "SYSTEM", "runtime", str(details.get("status", "Event complete"))
            events.append({"time": time_text, "kind": kind, "source": source, "message": message})
    return {
        "events": events[-100:],
        "terminal_output": "\n".join(_read_terminal_lines(200)),
        "iteration": iteration,
        "activeActions": active_actions,
        "provider": provider,
        "uptime": "LIVE",
        "progress": progress,
    }


HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus Terminal</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    height: 100%;
    background: #000;
    color: #00ff00;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 14px;
    line-height: 1.4;
    overflow: hidden;
  }
  #terminal {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 44px;
    padding: 12px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
  #input-line {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 44px;
    background: #000;
    border-top: 1px solid #00ff00;
    display: flex;
    align-items: center;
    padding: 0 12px;
  }
  #prompt { margin-right: 8px; }
  #message {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #00ff00;
    font-family: inherit;
    font-size: inherit;
    caret-color: #00ff00;
  }
</style>
</head>
<body>
  <div id="terminal"></div>
  <div id="input-line">
    <span id="prompt">&gt;</span>
    <input id="message" type="text" autocomplete="off" spellcheck="false" autofocus />
  </div>
<script>
  const terminal = document.getElementById('terminal');
  const input = document.getElementById('message');

  function scrollToBottom() {
    terminal.scrollTop = terminal.scrollHeight;
  }

  function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  async function loadState() {
    try {
      const res = await fetch('/api/state');
      const data = await res.json();
      terminal.textContent = data.terminal_output || '';
      scrollToBottom();
    } catch (e) {
      terminal.textContent = '[ERROR] Failed to load state: ' + e.message;
    }
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    try {
      const res = await fetch('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      terminal.textContent += '\\n> ' + escapeHtml(text) + '\\n' + escapeHtml(JSON.stringify(data, null, 2)) + '\\n';
      scrollToBottom();
    } catch (e) {
      terminal.textContent += '\\n> ' + escapeHtml(text) + '\\n[ERROR] ' + escapeHtml(e.message) + '\\n';
      scrollToBottom();
    }
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });

  document.addEventListener('click', () => input.focus());

  loadState();
  setInterval(loadState, 2000);
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/api/state"):
            self._handle_state()
        else:
            self._handle_index()

    def do_POST(self) -> None:
        if self.path.startswith("/api/events"):
            self._handle_events()
        else:
            self._send_json(404, {"status": "ERROR", "message": "Not found"})

    def _handle_index(self) -> None:
        body = HTML_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_state(self) -> None:
        try:
            payload = _build_dashboard_state()
        except Exception as exc:
            payload = {
                "terminal_output": f"[ERROR] Failed to read state: {exc}",
                "error": str(exc),
            }
        self._send_json(200, payload)

    def _handle_events(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")

            message = payload.get("message", payload.get("text", ""))
            event = {
                "type": payload.get("type", "USER_MESSAGE"),
                "source": payload.get("source", "dashboard"),
                "data": {"text": message} if message else payload.get("data", {}),
            }

            nexus_url = urljoin(NEXUS_RUNTIME_URL, "/message")
            req = Request(
                nexus_url,
                data=json.dumps(event).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            self._send_json(202, {"status": "ACCEPTED", "result": result})
        except Exception as exc:
            self._send_json(500, {"status": "ERROR", "message": str(exc)})

    def _send_json(self, status: int, obj: Any) -> None:
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", DASHBOARD_PORT), DashboardHandler)
    print(f"Nexus dashboard server listening on http://0.0.0.0:{DASHBOARD_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server shutdown requested.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()