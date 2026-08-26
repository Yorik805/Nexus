from __future__ import annotations

import os
from typing import Any

from .base import Orchestrator
from .dummy import DummyOrchestrator
from .gemini import GeminiConfig, GeminiOrchestrator
from .local import LocalOrchestrator
from .ollama import OllamaConfig, OllamaOrchestrator


def create_orchestrator(
    provider: str | None = None,
    config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """Construct the configured brain; Dummy remains the safe default."""
    selected = str(provider or os.getenv("ORCHESTRATOR_PROVIDER", "dummy")).strip().lower()
    if selected == "dummy":
        return DummyOrchestrator()
    if selected == "gemini":
        gemini_config = kwargs.pop("gemini_config", None)
        trace = kwargs.pop("trace", None)
        if gemini_config is None and isinstance(config, GeminiConfig):
            gemini_config = config
        elif gemini_config is None and isinstance(config, dict):
            allowed = {field for field in GeminiConfig.__dataclass_fields__}
            gemini_config = GeminiConfig(**{key: value for key, value in config.items() if key in allowed})
        return GeminiOrchestrator(config=gemini_config, trace=trace, **kwargs)
    if selected == "local":
        return LocalOrchestrator(config)
    if selected == "ollama":
        ollama_config = kwargs.pop("ollama_config", None)
        if ollama_config is None and isinstance(config, OllamaConfig):
            ollama_config = config
        return OllamaOrchestrator(config=ollama_config, trace=kwargs.pop("trace", None))
    raise ValueError(f"Unsupported orchestrator provider: {selected}")
