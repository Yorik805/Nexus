from __future__ import annotations

from .base import Orchestrator, OrchestratorContext, OrchestratorResult


class LocalOrchestrator(Orchestrator):
    """Reserved interface for a future local-model implementation."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        raise NotImplementedError("Local model integration is not implemented in Phase 2.")
