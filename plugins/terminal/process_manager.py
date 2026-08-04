"""Reusable process manager for Nexus terminal plugin."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from .process import Process
from .terminal_helpers import SandboxExecutor


class ProcessManager:
    def __init__(self, sandbox: SandboxExecutor | None = None) -> None:
        self._processes: dict[str, Process] = {}
        self._lock = threading.Lock()
        self._sandbox = sandbox or SandboxExecutor()

    def create_process(
        self,
        command: str | list[str],
        cwd: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: float | None = None,
        dynamic: bool = False,
        update_interval: int = 1000,
        conversation_updates: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Process:
        process = Process(
            command=command,
            cwd=cwd,
            environment=environment,
            timeout=timeout,
            dynamic=dynamic,
            update_interval=update_interval,
            conversation_updates=conversation_updates,
            metadata=metadata,
            sandbox=self._sandbox,
        )
        with self._lock:
            self._processes[process.process_id] = process

        process.start()
        return process

    def get_process(self, process_id: str) -> Process | None:
        with self._lock:
            return self._processes.get(process_id)

    def list_processes(self) -> list[dict[str, Any]]:
        with self._lock:
            return [process.to_dict() for process in self._processes.values()]

    def stop_process(self, process_id: str) -> bool:
        process = self.get_process(process_id)
        if process is None:
            return False
        process.stop()
        return True

    def update_process(
        self,
        process_id: str,
        update_interval: int | None = None,
        conversation_updates: bool | None = None,
        continue_flag: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        process = self.get_process(process_id)
        if process is None:
            return False

        with process._lock:
            if update_interval is not None:
                process.update_interval = update_interval
            if conversation_updates is not None:
                process.conversation_updates = conversation_updates
            if metadata is not None:
                process.metadata = metadata
            if continue_flag is not None:
                process.continue_flag = continue_flag
                if continue_flag is False and process.status == "RUNNING":
                    process.stop()

        return True

    def cleanup(self, older_than_seconds: float | None = None) -> list[str]:
        removed: list[str] = []
        cutoff = None
        if older_than_seconds is not None:
            cutoff = time.time() - older_than_seconds

        with self._lock:
            for process_id, process in list(self._processes.items()):
                if process.status in {"COMPLETED", "FAILED", "STOPPED", "TIMED_OUT"}:
                    if cutoff is None:
                        removed.append(process_id)
                    else:
                        if process.finished_at is None:
                            continue
                        finished_ts = datetime.fromisoformat(process.finished_at).timestamp()
                        if finished_ts <= cutoff:
                            removed.append(process_id)

            for process_id in removed:
                self._processes.pop(process_id, None)

        return removed


PROCESS_MANAGER = ProcessManager()
