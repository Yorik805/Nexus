from __future__ import annotations

from .base import Orchestrator, OrchestratorContext, OrchestratorResult


class GroqOrchestrator(Orchestrator):
    """Reserved interface for a future Groq-backed implementation."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        raise NotImplementedError("Groq integration is not implemented in Phase 2.")
