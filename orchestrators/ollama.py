from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ActionRequest, BackgroundTaskRequest, Orchestrator, OrchestratorContext, OrchestratorRequest, OrchestratorResult, ResponseRequest
from .prompt_loader import build_orchestrator_request


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "qwen2.5:1.5b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 180.0
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    max_output_tokens: int = 1024
    keep_alive: str | int = "10m"

    @classmethod
    def from_environment(cls) -> "OllamaConfig":
        import os

        return cls(
            model=os.getenv("OLLAMA_MODEL", cls.model),
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", cls.timeout_seconds)),
            max_retries=max(0, int(os.getenv("OLLAMA_MAX_RETRIES", cls.max_retries))),
            retry_backoff_seconds=max(0.0, float(os.getenv("OLLAMA_RETRY_BACKOFF_SECONDS", cls.retry_backoff_seconds))),
            max_output_tokens=max(1, int(os.getenv("OLLAMA_MAX_OUTPUT_TOKENS", cls.max_output_tokens))),
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", cls.keep_alive),
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
        attempts = self.config.max_retries + 1
        last_error: tuple[str, str] | None = None
        for _attempt in range(attempts):
            try:
                response = self._chat(request)
                result = self._parse_response(response)
                if self.trace:
                    self.trace("provider.response.parsed", event_id, provider="ollama", decision=result.decision, action_count=len(result.actions))
                return result
            except Exception as exc:
                code = self._classify_error(exc)
                if self.trace:
                    self.trace("provider.request.error", event_id, provider="ollama", error_code=code, error_type=type(exc).__name__)
                last_error = (code, str(exc))
                if code in {"UNAVAILABLE", "SERVER_ERROR", "TIMEOUT"} and _attempt + 1 < attempts:
                    time.sleep(self.config.retry_backoff_seconds * (2 ** _attempt))
                else:
                    break

        code, message = last_error or ("PROVIDER_ERROR", "Ollama request failed.")
        return OrchestratorResult(
            status="ERROR",
            complete=True,
            response=ResponseRequest(required=False, text=""),
            metadata={"error_code": code},
            error={"code": code, "message": message[:300]},
        )

    def _chat(self, request: OrchestratorRequest) -> dict[str, Any]:
        system = "\n\n".join((request.system_instruction, request.developer_instruction, request.schema_instruction))
        payload = {
            "model": self.config.model,
            "stream": False,
            "format": self._response_schema(request.context.get("runtime", {})),
            "options": {"num_predict": self.config.max_output_tokens},
            "keep_alive": self.config.keep_alive,
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
        content = content.strip()
        if not content:
            raise ValueError("Ollama returned empty message.content.")
        if content.startswith("```") and content.endswith("```"):
            content = content[3:-3].strip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()
        return json.loads(content)

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        message = str(exc).lower()
        name = type(exc).__name__.lower()
        if "timeout" in message or "timeout" in name:
            return "TIMEOUT"
        if "404" in message or "not found" in message:
            return "MODEL_NOT_FOUND"
        if "429" in message or "rate limit" in message:
            return "RATE_LIMITED"
        if "500" in message or "502" in message or "503" in message or "504" in message or "server error" in message:
            return "SERVER_ERROR"
        if "connect" in message or "network" in message or "unavailable" in message:
            return "UNAVAILABLE"
        if isinstance(exc, (json.JSONDecodeError, ValueError, TypeError, KeyError)):
            return "SCHEMA_VALIDATION_FAILED"
        return "PROVIDER_ERROR"

    @staticmethod
    def _response_schema(runtime_info: dict[str, Any]) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        plugins = runtime_info.get("plugins", {}) if isinstance(runtime_info, dict) else {}
        for plugin in plugins.values() if isinstance(plugins, dict) else []:
            contracts = plugin.get("contracts", {}) if isinstance(plugin, dict) else {}
            for contract in contracts.values() if isinstance(contracts, dict) else []:
                if isinstance(contract, dict):
                    properties.update(contract.get("required", {}))
                    properties.update(contract.get("optional", {}))
        return {
            "type": "object",
            "required": ["status", "complete", "response", "actions"],
            "properties": {
                "status": {"type": "string"},
                "complete": {"type": "boolean"},
                "decision": {"type": "string", "enum": ["CONTINUE", "NO_ACTION", "COMPLETE"]},
                "response": {"type": "object", "required": ["required", "text"], "additionalProperties": False, "properties": {"required": {"type": "boolean"}, "text": {"type": "string"}, "metadata": {"type": "object"}}},
                "actions": {"type": "array", "items": {"type": "object", "required": ["action_id", "plugin", "action", "data"], "additionalProperties": False, "properties": {"action_id": {"type": "string"}, "plugin": {"type": "string"}, "action": {"type": "string"}, "data": {"type": "object", "additionalProperties": False, "properties": properties}, "depends_on": {"type": "array", "items": {"type": "string"}}}}},
                "background_tasks": {"type": "array", "items": {"type": "object"}},
                "metadata": {"type": "object"},
            },
            "additionalProperties": False,
        }

    @staticmethod
    def _parse_response(raw: dict[str, Any]) -> OrchestratorResult:
        if not isinstance(raw, dict) or not isinstance(raw.get("response", {}), dict):
            raise ValueError("Ollama returned an invalid Nexus response.")
        actions = raw.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("Ollama actions must be an array.")
        if any(not isinstance(action, dict) for action in actions):
            raise ValueError("Ollama actions must contain only objects.")
        background_tasks = raw.get("background_tasks", [])
        if not isinstance(background_tasks, list) or any(not isinstance(task, dict) for task in background_tasks):
            raise ValueError("Ollama background_tasks must contain only objects.")
        response_data = raw["response"]
        decision = str(raw.get("decision", "COMPLETE" if raw.get("complete") else "CONTINUE")).upper()
        if decision not in {"CONTINUE", "NO_ACTION", "COMPLETE"}:
            raise ValueError("Ollama decision must be CONTINUE, NO_ACTION, or COMPLETE.")
        return OrchestratorResult(
            status=str(raw.get("status", "SUCCESS")),
            complete=bool(raw["complete"]),
            decision=decision,
            response=ResponseRequest(required=bool(response_data.get("required", True)), text=str(response_data.get("text", "")), metadata=response_data.get("metadata", {}) if isinstance(response_data.get("metadata", {}), dict) else {}),
            actions=[ActionRequest.from_dict(action) for action in actions],
            background_tasks=[BackgroundTaskRequest(task_type=str(task.get("task_type", "")), data=task.get("data", {}), task_id=str(task.get("task_id", ""))) for task in background_tasks],
            metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), dict) else {},
            error=raw.get("error") if isinstance(raw.get("error"), dict) else None,
        )

