from __future__ import annotations

from typing import Any

from .base import Orchestrator, OrchestratorContext, OrchestratorResult, ResponseRequest


class DummyOrchestrator(Orchestrator):
    """Deterministic placeholder brain with optional explicit test actions."""

    def __init__(self, test_actions: list[dict[str, Any]] | None = None) -> None:
        self.test_actions = test_actions or []

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        event_type = str(context.event.get("type", ""))
        text = (
            "Dummy orchestrator received your message."
            if event_type == "USER_MESSAGE"
            else "Dummy orchestrator processed a non-user event."
        )
        from .base import ActionRequest

        return OrchestratorResult(
            response=ResponseRequest(required=True, text=text),
            actions=[ActionRequest.from_dict(action) for action in self.test_actions],
            metadata={"intent": "DUMMY_RESPONSE"},
        )

    def handle(self, event: Any, context: dict[str, Any]) -> dict[str, Any]:
        """Compatibility adapter for the Phase 1 public behavior."""
        result = self.process(OrchestratorContext(
            event=event.to_dict() if hasattr(event, "to_dict") else dict(event),
            user_context=context.get("user_context", {}),
            memories=context.get("memories", []),
            working_context=context.get("working_context", {}),
            active_tasks=context.get("active_tasks", []),
            system_context=context.get("system_context", {}),
        ))
        payload = result.to_dict()
        payload["event_id"] = event.event_id if hasattr(event, "event_id") else context.get("event", {}).get("event_id")
        payload["response"]["text"] = result.response.text
        return payload
