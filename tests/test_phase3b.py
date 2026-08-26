from __future__ import annotations

import json

from orchestrators import (
    ActionRequest,
    GeminiConfig,
    GeminiOrchestrator,
    Orchestrator,
    OrchestratorContext,
    OrchestratorResult,
    create_orchestrator,
)
from orchestrators.credentials import CredentialPool


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.parsed = payload


class FakeModels:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models


def context() -> OrchestratorContext:
    return OrchestratorContext(
        event={"event_id": "event-1", "type": "USER_MESSAGE", "source": "test", "data": {"text": "find it"}},
        system_context={
            "runtime": {
                "plugins": {
                    "filesystem": {
                        "actions": ["READ", "WRITE"],
                        "contracts": {
                            "READ": {"required": {"path": {"type": "string"}}},
                            "WRITE": {"required": {"path": {"type": "string"}, "content": {"type": "string"}}},
                        },
                    }
                }
            }
        },
        working_context={"execution_history": [{"iteration": 1, "execution_results": []}]},
    )


def successful_payload() -> dict:
    return {
        "status": "SUCCESS",
        "complete": False,
        "response": {"required": False, "text": ""},
        "actions": [
            {"action_id": "one", "plugin": "filesystem", "action": "READ", "data": {"path": "x.txt"}},
            {"action_id": "two", "plugin": "memory", "action": "SEARCH", "data": {"query": "x"}, "depends_on": ["one"]},
        ],
        "metadata": {"intent": "LOOKUP"},
    }


def make_orchestrator(models: FakeModels, credentials=("key-a",)) -> GeminiOrchestrator:
    return GeminiOrchestrator(
        GeminiConfig(max_retries=0, retry_backoff_seconds=0),
        CredentialPool(credentials, cooldown_seconds=0),
        client_factory=lambda key: FakeClient(models),
    )


def test_gemini_implements_contract_and_maps_structured_output() -> None:
    models = FakeModels(FakeResponse(successful_payload()))
    result = make_orchestrator(models).process(context())

    assert isinstance(result, OrchestratorResult)
    assert result.complete is False
    assert [action.action_id for action in result.actions] == ["one", "two"]
    assert result.actions[1].depends_on == ["one"]
    assert models.calls[0]["model"] == "gemini-3.7-flash"
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"
    assert models.calls[0]["config"]["automatic_function_calling"] == {"disable": True}
    assert "tools" not in models.calls[0]["config"]
    data_schema = models.calls[0]["config"]["response_schema"]["properties"]["actions"]["items"]["properties"]["data"]
    assert "path" in data_schema["properties"]
    assert "content" in data_schema["properties"]
    assert "Nexus is an AI operating system orchestrator" in models.calls[0]["config"]["system_instruction"]
    assert json.loads(models.calls[0]["contents"])["event"]["event_id"] == "event-1"


def test_gemini_maps_complete_response() -> None:
    payload = successful_payload()
    payload["complete"] = True
    payload["actions"] = []
    payload["response"] = {"required": True, "text": "Done."}
    result = make_orchestrator(FakeModels(FakeResponse(payload))).process(context())
    assert result.complete is True
    assert result.response.text == "Done."
    assert result.actions == []


def test_gemini_accepts_fenced_json_without_silently_accepting_malformed_actions() -> None:
    payload = json.dumps(successful_payload())
    result = make_orchestrator(FakeModels(FakeResponse(f"```json\n{payload}\n```"))).process(context())
    assert result.actions[0].data["path"] == "x.txt"
    malformed = make_orchestrator(FakeModels(FakeResponse({**successful_payload(), "actions": ["bad"]}))).process(context())
    assert malformed.status == "ERROR"
    assert malformed.error["code"] == "SCHEMA_VALIDATION_FAILED"


def test_malformed_response_is_structured_error() -> None:
    result = make_orchestrator(FakeModels(FakeResponse({"status": "SUCCESS"}))).process(context())
    assert result.status == "ERROR"
    assert result.error["code"] == "SCHEMA_VALIDATION_FAILED"
    assert "key-a" not in str(result)


def test_timeout_is_structured_error_without_crashing() -> None:
    result = make_orchestrator(FakeModels(error=TimeoutError("request timeout"))).process(context())
    assert result.status == "ERROR"
    assert result.error["code"] == "TIMEOUT"


def test_rate_limit_fails_over_to_another_credential() -> None:
    models = FakeModels(FakeResponse(successful_payload()))
    keys_used: list[str] = []

    def factory(key: str):
        keys_used.append(key)
        if key == "key-a":
            raise RuntimeError("429 rate limit")
        return FakeClient(models)

    orchestrator = GeminiOrchestrator(
        GeminiConfig(max_retries=1, retry_backoff_seconds=0),
        CredentialPool(["key-a", "key-b"], cooldown_seconds=0),
        client_factory=factory,
    )
    result = orchestrator.process(context())
    assert result.status == "SUCCESS"
    assert keys_used == ["key-a", "key-b"]
    assert "key-a" not in str(result)
    assert "key-b" not in str(result)


def test_all_credentials_unavailable_is_clean_failure() -> None:
    pool = CredentialPool([], cooldown_seconds=0)
    result = GeminiOrchestrator(
        GeminiConfig(max_retries=0, retry_backoff_seconds=0),
        pool,
        client_factory=lambda key: None,
    ).process(context())
    assert result.status == "ERROR"
    assert result.error["code"] == "CREDENTIALS_UNAVAILABLE"


def test_provider_factory_keeps_dummy_default_and_supports_gemini() -> None:
    assert isinstance(create_orchestrator("dummy"), Orchestrator)
    assert isinstance(create_orchestrator("gemini", gemini_config=GeminiConfig(), credential_pool=CredentialPool([])), GeminiOrchestrator)
