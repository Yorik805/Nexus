from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import Orchestrator, OrchestratorContext, OrchestratorRequest, OrchestratorResult, ResponseRequest
from .prompt_loader import build_orchestrator_request


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "qwen2.5:1.5b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 180.0

    @classmethod
    def from_environment(cls) -> "OllamaConfig":
        import os

        return cls(
            model=os.getenv("OLLAMA_MODEL", cls.model),
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", cls.timeout_seconds)),
        )


class OllamaOrchestrator(Orchestrator):
    """Ollama adapter using the provider-neutral Nexus request contract."""

    def __init__(self, config: OllamaConfig | None = None, trace: Callable[..., None] | None = None) -> None:
        self.config = config or OllamaConfig.from_environment()
        self.trace = trace

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        request = build_orchestrator_request(context)
        event_id = context.event.get("event_id")
        if self.trace:
            self.trace("provider.request.start", event_id, provider="ollama", model=self.config.model)
        try:
            response = self._chat(request)
            result = self._parse_response(response)
            if self.trace:
                self.trace("provider.response.parsed", event_id, provider="ollama", decision=result.decision, action_count=len(result.actions))
            return result
        except Exception as exc:
            if self.trace:
                self.trace("provider.request.error", event_id, provider="ollama", error_type=type(exc).__name__)
            return OrchestratorResult(
                status="ERROR",
                complete=True,
                response=ResponseRequest(required=False, text=""),
                metadata={"error_code": "OLLAMA_PROVIDER_ERROR"},
                error={"code": "OLLAMA_PROVIDER_ERROR", "message": str(exc)[:300]},
            )

    def _chat(self, request: OrchestratorRequest) -> dict[str, Any]:
        system = "\n\n".join((request.system_instruction, request.developer_instruction, request.schema_instruction))
        payload = {
            "model": self.config.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({"context": request.context, "current_event": request.current_event}, default=str)},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        try:
            http_request = Request(f"{self.config.base_url.rstrip('/')}/api/chat", data=body, method="POST", headers={"Content-Type": "application/json"})
            with urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Ollama returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not connect to Ollama: {exc.reason}") from exc
        message = result.get("message", {}) if isinstance(result, dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ValueError("Ollama response did not contain message.content.")
        return json.loads(content.strip())

    @staticmethod
    def _parse_response(raw: dict[str, Any]) -> OrchestratorResult:
        if not isinstance(raw, dict) or not isinstance(raw.get("response", {}), dict):
            raise ValueError("Ollama returned an invalid Nexus response.")
        actions = raw.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("Ollama actions must be an array.")
        from .gemini import GeminiOrchestrator
        return GeminiOrchestrator._parse_response(type("Response", (), {"parsed": raw})())

