from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Callable

from .base import (
    ActionRequest,
    BackgroundTaskRequest,
    Orchestrator,
    OrchestratorContext,
    OrchestratorRequest,
    OrchestratorResult,
    ResponseRequest,
)
from .credentials import CredentialPool
from .prompt_loader import build_orchestrator_request


@dataclass(frozen=True)
class GeminiConfig:
    model: str = "gemini-3.6-flash"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    max_output_tokens: int = 8192
    credential_cooldown_seconds: float = 30.0

    @classmethod
    def from_environment(cls) -> "GeminiConfig":
        import os

        return cls(
            model=os.getenv("GEMINI_MODEL", cls.model),
            timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", cls.timeout_seconds)),
            max_retries=max(0, int(os.getenv("GEMINI_MAX_RETRIES", cls.max_retries))),
            retry_backoff_seconds=max(0.0, float(os.getenv("GEMINI_RETRY_BACKOFF_SECONDS", cls.retry_backoff_seconds))),
            max_output_tokens=max(1, int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", cls.max_output_tokens))),
            credential_cooldown_seconds=max(0.0, float(os.getenv("GEMINI_CREDENTIAL_COOLDOWN_SECONDS", cls.credential_cooldown_seconds))),
        )


class GeminiOrchestrator(Orchestrator):
    """Gemini brain that returns Nexus decisions and never executes plugins."""

    def __init__(
        self,
        config: GeminiConfig | None = None,
        credential_pool: CredentialPool | None = None,
        client_factory: Callable[[str], Any] | None = None,
        trace: Callable[..., None] | None = None,
    ) -> None:
        self.config = config or GeminiConfig.from_environment()
        self.credentials = credential_pool if credential_pool is not None else CredentialPool.from_environment(self.config.credential_cooldown_seconds)
        self._client_factory = client_factory or self._default_client_factory
        self.trace = trace

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        if not self.credentials.has_credentials():
            return self._error("CREDENTIALS_UNAVAILABLE", "No Gemini API credential is configured.")

        request = build_orchestrator_request(context)
        if self.trace:
            self.trace("provider.request.start", context.event.get("event_id"), provider="gemini", model=self.config.model)
        max_attempts = max(len(self.credentials), self.config.max_retries + 1)
        last_error: tuple[str, str] | None = None
        attempt = 0
        while attempt < max_attempts:
            credential = self.credentials.acquire()
            if credential is None:
                return self._error("CREDENTIALS_UNAVAILABLE", "All Gemini API credentials are temporarily unavailable.")
            try:
                client = self._client_factory(credential.value)
                response = self._generate(client, request)
                raw_text = getattr(response, "text", "") or ""
                if self.trace:
                    self.trace("provider.response.received", context.event.get("event_id"), provider="gemini", parsed_present=getattr(response, "parsed", None) is not None, text_length=len(raw_text), response_text=raw_text[:2000])
                result = self._parse_response(response)
                if self.trace:
                    self.trace("provider.response.parsed", context.event.get("event_id"), provider="gemini", decision=result.decision, action_count=len(result.actions))
                self.credentials.mark_success(credential)
                return result
            except Exception as exc:
                code = self._classify_error(exc)
                if self.trace:
                    self.trace("provider.request.error", context.event.get("event_id"), provider="gemini", error_code=code, error_type=type(exc).__name__)
                last_error = (code, str(exc))
                print(f"[NEXUS:gemini.error] event_id={context.event.get('event_id')} code={code} type={type(exc).__name__} message={exc}")
                if code in {"AUTHENTICATION_FAILED", "RATE_LIMITED", "RESOURCE_EXHAUSTED", "UNAVAILABLE"}:
                    self.credentials.mark_unavailable(credential)
                if code == "SCHEMA_VALIDATION_FAILED":
                    break
                if attempt + 1 < max_attempts:
                    time.sleep(self.config.retry_backoff_seconds * (2 ** attempt))
                print(f"[NEXUS:gemini.retry] event_id={context.event.get('event_id')} attempt={attempt + 1}/{max_attempts} error={code} model={self.config.model}")
            attempt += 1

        code, message = last_error or ("PROVIDER_ERROR", "Gemini request failed.")
        return self._error(code, "Gemini request failed without exposing credentials.", details=message)

    def _generate(self, client: Any, request: OrchestratorRequest) -> Any:
        runtime_info = request.context.get("runtime", {})
        schema = self._response_schema(runtime_info)
        config = {
            "system_instruction": "\n\n".join((request.system_instruction, request.developer_instruction, request.schema_instruction)),
            "response_mime_type": "application/json",
            "response_schema": schema,
            "automatic_function_calling": {"disable": True},
            "max_output_tokens": self.config.max_output_tokens,
        }
        return client.models.generate_content(
            model=self.config.model,
            contents=json.dumps({"context": request.context, "current_event": request.current_event, "event": request.current_event}, sort_keys=True, default=str),
            config=config,
        )

    @staticmethod
    def _response_schema(runtime_info: dict[str, Any] | None = None) -> dict[str, Any]:
        contracts = runtime_info.get("plugins", {}) if isinstance(runtime_info, dict) else {}
        data_properties: dict[str, Any] = {}
        for plugin in contracts.values() if isinstance(contracts, dict) else []:
            for contract in plugin.get("contracts", {}).values() if isinstance(plugin, dict) else []:
                for name, field_schema in {**contract.get("required", {}), **contract.get("optional", {})}.items():
                    data_properties.setdefault(name, field_schema)
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "complete": {"type": "boolean"},
                "decision": {"type": "string", "enum": ["CONTINUE", "NO_ACTION", "COMPLETE"]},
                "response": {
                    "type": "object",
                    "properties": {
                        "required": {"type": "boolean"},
                        "text": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                    "required": ["required", "text"],
                },
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_id": {"type": "string"},
                            "plugin": {"type": "string"},
                            "action": {"type": "string"},
                            "data": {
                                "type": "object",
                                "properties": data_properties,
                                "description": "Use the required and optional fields from the supplied plugin action contract.",
                            },
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["action_id", "plugin", "action", "data"],
                    },
                },
                "background_tasks": {"type": "array", "items": {"type": "object"}},
                "metadata": {"type": "object"},
            },
            "required": ["status", "complete", "response", "actions"],
        }

    @staticmethod
    def _parse_response(response: Any) -> OrchestratorResult:
        raw = getattr(response, "parsed", None)
        if raw is None:
            raw = getattr(response, "text", None)
        if isinstance(raw, str):
            raw = raw.strip()
            if "```json" in raw:
                start = raw.find("```json") + 7
                end = raw.find("```", start)
                if end != -1:
                    raw = raw[start:end].strip()
            elif raw.startswith("```") and raw.endswith("```"):
                raw = raw[3:-3].strip()
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise ValueError("Gemini returned a non-object structured response.")
        response_data = raw.get("response", {})
        if not isinstance(response_data, dict):
            raise ValueError("Gemini response field must be an object.")
        actions = raw.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("Gemini actions field must be an array.")
        background_tasks = raw.get("background_tasks", [])
        if not isinstance(background_tasks, list):
            raise ValueError("Gemini background_tasks field must be an array.")
        if any(not isinstance(action, dict) for action in actions):
            raise ValueError("Gemini actions must contain only objects.")
        if any(not isinstance(task, dict) for task in background_tasks):
            raise ValueError("Gemini background_tasks must contain only objects.")
        decision = str(raw.get("decision", "COMPLETE" if bool(raw.get("complete", False)) else "CONTINUE")).upper()
        if decision not in {"CONTINUE", "NO_ACTION", "COMPLETE"}:
            raise ValueError("Gemini decision must be CONTINUE, NO_ACTION, or COMPLETE.")
        return OrchestratorResult(
            status=str(raw.get("status", "SUCCESS")),
            complete=bool(raw["complete"]),
            response=ResponseRequest(
                required=bool(response_data.get("required", True)),
                text=str(response_data.get("text", "")),
                metadata=response_data.get("metadata", {}) if isinstance(response_data.get("metadata", {}), dict) else {},
            ),
            actions=[ActionRequest.from_dict(action) for action in actions],
            background_tasks=[BackgroundTaskRequest(task_type=str(task.get("task_type", "")), data=task.get("data", {}), task_id=str(task.get("task_id", ""))) for task in background_tasks],
            metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), dict) else {},
            error=raw.get("error") if isinstance(raw.get("error"), dict) else None,
            decision=decision,
        )

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        message = str(exc).lower()
        name = type(exc).__name__.lower()
        if "timeout" in message or "timeout" in name:
            return "TIMEOUT"
        if "401" in message or "403" in message or "auth" in message or "api key" in message:
            return "AUTHENTICATION_FAILED"
        if "400" in message and "invalid_argument" in message:
            return "SCHEMA_VALIDATION_FAILED"
        if "429" in message or "rate" in message:
            return "RATE_LIMITED"
        if "resource exhausted" in message or "quota" in message:
            return "RESOURCE_EXHAUSTED"
        if "connect" in message or "network" in message or "unavailable" in message:
            return "UNAVAILABLE"
        if isinstance(exc, (json.JSONDecodeError, ValueError, TypeError, KeyError)):
            return "SCHEMA_VALIDATION_FAILED"
        return "PROVIDER_ERROR"

    @staticmethod
    def _error(code: str, message: str, details: str | None = None) -> OrchestratorResult:
        metadata: dict[str, Any] = {"error_code": code}
        if details:
            metadata["provider_error"] = details[:500]
        return OrchestratorResult(
            status="ERROR",
            complete=True,
            response=ResponseRequest(required=False, text=""),
            metadata=metadata,
            error={"code": code, "message": message},
        )

    def _default_client_factory(self, api_key: str) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is required for Gemini orchestration.") from exc
        return genai.Client(
            api_key=api_key,
            http_options={"timeout": int(self.config.timeout_seconds * 1000)},
        )


