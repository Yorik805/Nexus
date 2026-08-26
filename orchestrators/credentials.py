from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Iterable


@dataclass
class CredentialState:
    value: str
    unavailable_until: float = 0.0
    failures: int = 0


class CredentialPool:
    """In-memory API-key pool with bounded cooldown failover."""

    def __init__(
        self,
        credentials: Iterable[str] | None = None,
        cooldown_seconds: float = 30.0,
    ) -> None:
        values = credentials if credentials is not None else self._environment_credentials()
        self._credentials = [CredentialState(value.strip()) for value in values if value and value.strip()]
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._index = 0

    @classmethod
    def from_environment(cls, cooldown_seconds: float = 30.0) -> "CredentialPool":
        return cls(None, cooldown_seconds)

    def acquire(self) -> CredentialState | None:
        if not self._credentials:
            return None
        now = time.monotonic()
        for offset in range(len(self._credentials)):
            index = (self._index + offset) % len(self._credentials)
            state = self._credentials[index]
            if state.unavailable_until <= now:
                self._index = (index + 1) % len(self._credentials)
                return state
        return None

    def mark_success(self, state: CredentialState) -> None:
        state.failures = 0
        state.unavailable_until = 0.0

    def mark_unavailable(self, state: CredentialState) -> None:
        state.failures += 1
        state.unavailable_until = time.monotonic() + self.cooldown_seconds

    def has_credentials(self) -> bool:
        return bool(self._credentials)

    @staticmethod
    def _environment_credentials() -> list[str]:
        multiple = os.getenv("GEMINI_API_KEYS", "")
        if multiple.strip():
            return [value for value in multiple.split(",") if value.strip()]
        single = os.getenv("GEMINI_API_KEY", "")
        return [single] if single.strip() else []
