from __future__ import annotations

import inspect
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class RuntimeTrace:
    """Persist precise, terminal-exact runtime pipeline events as JSON lines."""

    def __init__(self, path: str | Path = "logs/nexus_runtime.log") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._log_date: str | None = None

    def _check_rotation(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._log_date == today:
            return
        if self._log_date is not None and self.path.exists() and self.path.stat().st_size > 0:
            dated_path = self.path.parent / f"{self.path.stem}_{self._log_date}{self.path.suffix}"
            try:
                self.path.rename(dated_path)
            except FileNotFoundError:
                pass
        self._log_date = today
        self._cleanup_old_logs()

    def _cleanup_old_logs(self) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - 7 * 24 * 60 * 60
        stem = self.path.stem
        for entry_path in self.path.parent.glob(f"{stem}_*.log"):
            try:
                if entry_path.stat().st_mtime < cutoff:
                    entry_path.unlink()
            except OSError:
                pass

    def _caller_function_name(self) -> str | None:
        frame = inspect.currentframe()
        if frame is None:
            return None
        caller = frame.f_back
        if caller is None:
            return None
        return caller.f_code.co_qualname

    def record(self, step: str, event_id: str | None = None, **details: Any) -> None:
        self._check_rotation()
        if "function" not in details:
            function_name = self._caller_function_name()
            if function_name is not None:
                details = {**details, "function": function_name}
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "event_id": event_id,
            "details": details,
        }
        line = json.dumps(entry, sort_keys=True, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        print(f"[NEXUS:{step}] {json.dumps(entry['details'], sort_keys=True, default=str)}")

    def record_exception(
        self,
        step: str,
        event_id: str | None = None,
        exc: Exception | None = None,
        **details: Any,
    ) -> None:
        if exc is not None:
            details["error_type"] = type(exc).__name__
            details["error_message"] = str(exc)
            details["error_traceback"] = traceback.format_exc()
        self.record(step, event_id, **details)
