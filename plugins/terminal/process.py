"""Terminal process model for Nexus."""

from __future__ import annotations

import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .terminal_helpers import SandboxExecutor


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Process:
    def __init__(
        self,
        command: str | list[str],
        cwd: str | Path | None,
        environment: dict[str, str] | None,
        timeout: float | None,
        dynamic: bool,
        update_interval: int,
        conversation_updates: bool,
        metadata: dict[str, Any] | None,
        sandbox: SandboxExecutor | None = None,
    ):
        self.process_id = str(uuid.uuid4())
        self.command = command
        self.cwd = str(cwd) if cwd is not None else None
        self.environment = environment or {}
        self.status = "PENDING"
        self.pid: int | None = None
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.stdout = ""
        self.stderr = ""
        self.exit_code: int | None = None
        self.runtime: float | None = None
        self.dynamic = dynamic
        self.update_interval = update_interval
        self.continue_flag = True
        self.conversation_updates = conversation_updates
        self.metadata = metadata or {}
        self.timeout = timeout
        self.message: str | None = None

        self._sandbox = sandbox or SandboxExecutor()
        self._process: subprocess.Popen | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None
        self._timeout_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.status != "PENDING":
                return

            try:
                self._process = self._sandbox.launch(
                    self.command,
                    self.cwd,
                    self.environment,
                )
            except Exception as exc:
                self.status = "FAILED"
                self.message = f"Failed to launch command: {exc}"
                self.finished_at = _timestamp()
                self.runtime = 0.0
                return

            self.pid = self._process.pid
            self.started_at = _timestamp()
            self.status = "RUNNING"

            self._stdout_thread = threading.Thread(
                target=self._read_stream,
                args=(self._process.stdout, "stdout"),
                daemon=True,
            )
            self._stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(self._process.stderr, "stderr"),
                daemon=True,
            )
            self._stdout_thread.start()
            self._stderr_thread.start()

            self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
            self._monitor_thread.start()

            if self.timeout is not None and self.timeout > 0:
                self._timeout_thread = threading.Thread(target=self._timeout_watcher, daemon=True)
                self._timeout_thread.start()

    def _read_stream(self, stream: Any, target: str) -> None:
        try:
            while True:
                line = stream.readline()
                if line == "" or line is None:
                    break
                with self._lock:
                    if target == "stdout":
                        self.stdout += line
                    else:
                        self.stderr += line
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _monitor(self) -> None:
        assert self._process is not None
        try:
            exit_code = self._process.wait()
            with self._lock:
                if self.status in {"STOPPED", "TIMED_OUT", "FAILED"} and self.finished_at is not None:
                    self.exit_code = exit_code if self.exit_code is None else self.exit_code
                    self.runtime = self._compute_runtime()
                    return

                self.exit_code = exit_code
                self.finished_at = _timestamp()
                self.runtime = self._compute_runtime()
                self.status = "COMPLETED" if exit_code == 0 else "FAILED"
        except Exception:
            with self._lock:
                if self.status == "RUNNING":
                    self.status = "FAILED"
                    self.message = "Process monitor failed."
                    self.finished_at = _timestamp()
                    self.runtime = self._compute_runtime()

    def _timeout_watcher(self) -> None:
        assert self._process is not None
        try:
            self._process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            with self._lock:
                if self.status != "RUNNING":
                    return
                self.continue_flag = False
                self.status = "TIMED_OUT"
                self.message = f"Process timed out after {self.timeout} seconds."
            self._terminate_process()
        except Exception:
            pass

    def _terminate_process(self) -> None:
        if self._process is None:
            return

        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
        except Exception:
            pass

    def stop(self) -> None:
        with self._lock:
            if self.status not in {"RUNNING"}:
                return
            self.continue_flag = False
            self.status = "STOPPED"
            self.message = "Process was stopped by user."

        self._terminate_process()

        with self._lock:
            if self.finished_at is None:
                self.finished_at = _timestamp()
            self.runtime = self._compute_runtime()

    def wait_for_completion(self) -> None:
        if self._monitor_thread is not None:
            self._monitor_thread.join()
        if self._stdout_thread is not None:
            self._stdout_thread.join()
        if self._stderr_thread is not None:
            self._stderr_thread.join()

    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def _compute_runtime(self) -> float | None:
        if self.started_at is None:
            return None

        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.finished_at) if self.finished_at else datetime.now(timezone.utc)
        return max((end - start).total_seconds(), 0.0)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "process_id": self.process_id,
                "command": self.command,
                "cwd": self.cwd,
                "environment": self.environment,
                "status": self.status,
                "pid": self.pid,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "stdout": self.stdout,
                "stderr": self.stderr,
                "exit_code": self.exit_code,
                "runtime": self.runtime,
                "dynamic": self.dynamic,
                "update_interval": self.update_interval,
                "continue_flag": self.continue_flag,
                "conversation_updates": self.conversation_updates,
                "metadata": self.metadata,
                "message": self.message or "",
            }
