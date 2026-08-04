"""Terminal plugin sandbox and command helpers."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any


class SandboxExecutor:
    """Sandbox abstraction for launching subprocesses.

    The current implementation uses Python subprocess directly. Future
    implementations can replace this class with Docker, Firejail, bubblewrap,
    or other sandbox layers without changing the terminal plugin API.
    """

    def launch(
        self,
        command: str | list[str],
        cwd: str | Path | None,
        environment: dict[str, str] | None,
    ) -> subprocess.Popen:
        args = self._normalize_command(command)
        cwd_path = self._normalize_cwd(cwd)
        env = self._normalize_environment(environment)

        return subprocess.Popen(
            args,
            cwd=str(cwd_path) if cwd_path is not None else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

    def _normalize_command(self, command: str | list[str]) -> list[str]:
        if isinstance(command, str):
            if not command.strip():
                raise ValueError("command must be a non-empty string")
            return shlex.split(command)

        if isinstance(command, list):
            if not command:
                raise ValueError("command list must not be empty")
            return [str(part) for part in command]

        raise ValueError("command must be a string or a list of strings")

    def _normalize_cwd(self, cwd: str | Path | None) -> Path | None:
        if cwd is None:
            return None

        normalized = Path(cwd).expanduser().resolve()
        if not normalized.exists():
            raise ValueError(f"Working directory does not exist: {cwd}")
        return normalized

    def _normalize_environment(self, environment: dict[str, str] | None) -> dict[str, str] | None:
        if environment is None:
            return None

        return {str(key): str(value) for key, value in environment.items()}
