from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping
import uuid


@dataclass(frozen=True)
class ActionRequest:
    """One plugin operation proposed by an orchestrator."""

    plugin: str
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionRequest":
        return cls(
            action_id=str(value.get("action_id") or uuid.uuid4()),
            plugin=str(value.get("plugin", "")),
            action=str(value.get("action", "")),
            data=dict(value.get("data", {})),
            depends_on=[str(item) for item in value.get("depends_on", [])],
        )


@dataclass(frozen=True)
class BackgroundTaskRequest:
    """Future background work request; execution is intentionally deferred."""

    task_type: str
    data: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResponseRequest:
    required: bool = True
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrchestratorContext:
    """Standardized input available to any orchestrator implementation."""

    event: dict[str, Any]
    user_context: dict[str, Any] = field(default_factory=dict)
    memories: list[dict[str, Any]] = field(default_factory=list)
    working_context: dict[str, Any] = field(default_factory=dict)
    active_tasks: list[dict[str, Any]] = field(default_factory=list)
    system_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrchestratorResult:
    status: str = "SUCCESS"
    response: ResponseRequest = field(default_factory=ResponseRequest)
    actions: list[ActionRequest] = field(default_factory=list)
    background_tasks: list[BackgroundTaskRequest] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result


class Orchestrator(ABC):
    """Replaceable intelligence boundary for Nexus."""

    @abstractmethod
    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        """Turn standardized context into a structured decision."""
        raise NotImplementedError
