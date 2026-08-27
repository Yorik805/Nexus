from __future__ import annotations

from typing import Any, Callable

from .ollama import OllamaConfig, OllamaOrchestrator


class LocalOrchestrator(OllamaOrchestrator):
    """Local-model orchestrator backed by the Ollama HTTP API."""

    def __init__(self, config: OllamaConfig | dict[str, Any] | None = None, trace: Callable[..., None] | None = None) -> None:
        if isinstance(config, dict):
            config = OllamaConfig(**{key: value for key, value in config.items() if key in OllamaConfig.__dataclass_fields__})
        super().__init__(config=config, trace=trace)
