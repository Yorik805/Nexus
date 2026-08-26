from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class RuntimeTrace:
    """Persist concise, non-sensitive runtime pipeline events as JSON lines."""

    def __init__(self, path: str | Path = "logs/nexus_runtime.log") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def record(self, step: str, event_id: str | None = None, **details: Any) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "event_id": event_id,
            "details": self._safe(details),
        }
        line = json.dumps(entry, sort_keys=True, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        print(f"[NEXUS:{step}] {json.dumps(entry['details'], sort_keys=True, default=str)}")

    @classmethod
    def _safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): cls._safe(item) for key, item in value.items() if str(key).lower() not in {"text", "content", "api_key", "provider_error"}}
        if isinstance(value, list):
            return [cls._safe(item) for item in value[:20]]
        if isinstance(value, str):
            return value[:300]
        return value
