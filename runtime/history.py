from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextHistoryManager:
    """Keep recent execution detail while compacting older cycle records."""

    recent_limit: int = 20
    historical_summary: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.recent_limit < 1:
            raise ValueError("recent_limit must be at least 1.")
        self._records: list[dict[str, Any]] = []
        self.compression_count = 0

    def append(self, record: dict[str, Any]) -> None:
        self._records.append(record)
        if len(self._records) > self.recent_limit:
            self._compact(self._records.pop(0))

    def extend(self, records: list[dict[str, Any]]) -> None:
        for record in records:
            self.append(record)

    def recent(self) -> list[dict[str, Any]]:
        return list(self._records)

    def context(self) -> dict[str, Any]:
        summary = " ".join(self.historical_summary)
        return {
            "historical_summary": summary,
            "recent_execution_history": self.recent(),
            "compression": {
                "occurred": self.compression_count > 0,
                "summary_items": len(self.historical_summary),
                "recent_count": len(self._records),
            },
        }

    def records(self) -> list[dict[str, Any]]:
        return self.recent()

    def _compact(self, record: dict[str, Any]) -> None:
        iteration = record.get("iteration", "?")
        results = record.get("execution_results", [])
        facts: list[str] = []
        for result in results:
            action_id = result.get("action_id", "unknown")
            status = result.get("status", "UNKNOWN")
            message = str(result.get("message", "")).strip()
            fact = f"iteration {iteration}: {action_id}={status}"
            if message:
                fact += f" ({message[:160]})"
            facts.append(fact)
        if facts:
            self.historical_summary.extend(facts)
        self.compression_count += 1
