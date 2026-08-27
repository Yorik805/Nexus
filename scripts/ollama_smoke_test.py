from __future__ import annotations

import json
import sys
import traceback
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Ensure project root is on path so we can import Nexus modules
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from orchestrators.ollama import OllamaConfig, OllamaOrchestrator
from orchestrators.base import Orchestrator, OrchestratorContext, OrchestratorResult, ResponseRequest
from orchestrators.local import LocalOrchestrator
from runtime import NexusRuntime, PluginRegistry


class _CompleteAfterFirstCallOrchestrator(Orchestrator):
    def __init__(self, wrapped: OllamaOrchestrator) -> None:
        self._wrapped = wrapped
        self._first_call_done = False

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        result = self._wrapped.process(context)
        if not self._first_call_done and result.status != "ERROR":
            self._first_call_done = True
            return OrchestratorResult(
                status=result.status,
                complete=True,
                response=result.response,
                actions=result.actions,
                background_tasks=result.background_tasks,
                metadata=result.metadata,
                error=result.error,
                decision="COMPLETE",
            )
        return result


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, bytes]:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _http_post(url: str, payload: dict[str, Any], timeout: float = 30.0) -> tuple[int, bytes]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def step(label: str):
    print(f"\n=== {label} ===")


def report(name: str, passed: bool, error: Exception | None = None) -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if error is not None:
        print(f"  Error: {type(error).__name__}: {error}")
    return passed


def check_ollama_reachable(base_url: str) -> bool:
    step("Step 1: Ollama server reachability")
    try:
        status, body = _http_get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
        print(f"  GET /api/tags -> HTTP {status} ({len(body)} bytes)")
        return report("Ollama server is reachable", True)
    except HTTPError as exc:
        return report("Ollama server is reachable", False, exc)
    except URLError as exc:
        print(f"  Could not connect: {exc.reason}")
        print("  Hint: is ollama serve running? Check OLLAMA_BASE_URL if non-default.")
        return report("Ollama server is reachable", False, exc)
    except Exception as exc:
        return report("Ollama server is reachable", False, exc)


def check_model_exists(config: OllamaConfig) -> bool:
    step("Step 2: Configured model exists")
    try:
        status, body = _http_get(f"{config.base_url.rstrip('/')}/api/tags", timeout=5.0)
        data = json.loads(body.decode("utf-8"))
        models = data.get("models", []) if isinstance(data, dict) else []
        names = [m.get("name", "") for m in models if isinstance(m, dict)]
        # Ollama tags may include a trailing ':latest' or similar tag
        short_names = {n.split(":")[0] for n in names}
        print(f"  Configured model: {config.model}")
        print(f"  Available models: {names}")
        if config.model in names or config.model.split(":")[0] in short_names:
            return report("Configured model is available", True)
        return report("Configured model is available", False, RuntimeError(f"Model {config.model!r} not in tags"))
    except Exception as exc:
        return report("Configured model is available", False, exc)


def check_direct_chat_request(config: OllamaConfig) -> bool:
    step("Step 3: Direct Nexus schema-constrained request to /api/chat")
    print("  Note: CPU-only Ollama can be slow; using configured timeout.")
    try:
        payload = {
            "model": config.model,
            "stream": False,
            "format": {
                "type": "object",
                "required": ["status", "complete", "response", "actions"],
                "properties": {
                    "status": {"type": "string"},
                    "complete": {"type": "boolean"},
                    "decision": {"type": "string", "enum": ["CONTINUE", "NO_ACTION", "COMPLETE"]},
                    "response": {
                        "type": "object",
                        "required": ["required", "text"],
                        "additionalProperties": False,
                        "properties": {
                            "required": {"type": "boolean"},
                            "text": {"type": "string"},
                            "metadata": {"type": "object"},
                        },
                    },
                    "actions": {"type": "array", "items": {"type": "object"}},
                    "background_tasks": {"type": "array", "items": {"type": "object"}},
                    "metadata": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "options": {"num_predict": 256},
            "keep_alive": "5m",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the Nexus Orchestrator. Return a minimal valid "
                        "OrchestratorResult JSON with status=SUCCESS, complete=true, "
                        "decision=COMPLETE, response.required=false, response.text='ok', "
                        "and actions=[]."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "context": {"runtime": {"plugins": {}}},
                            "current_event": {"type": "USER_MESSAGE", "data": {"text": "ping"}},
                        },
                        default=str,
                    ),
                },
            ],
        }
        status, body = _http_post(
            f"{config.base_url.rstrip('/')}/api/chat",
            payload,
            timeout=config.timeout_seconds,
        )
        print(f"  POST /api/chat -> HTTP {status} ({len(body)} bytes)")
        raw = json.loads(body.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Response is not a JSON object")
        message = raw.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        if not content:
            raise ValueError("Empty message.content in response")
        # Strip optional markdown fences
        content = content.strip()
        if content.startswith("`") and content.endswith("`"):
            content = content[3:-3].strip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()
        parsed = json.loads(content)
        required_keys = {"status", "complete", "response", "actions"}
        missing = required_keys - set(parsed.keys())
        if missing:
            raise ValueError(f"Missing required keys in response: {missing}")
        print(f"  Parsed response status={parsed.get('status')}, complete={parsed.get('complete')}")
        return report("Schema-constrained chat request returned valid JSON", True)
    except Exception as exc:
        return report("Schema-constrained chat request returned valid JSON", False, exc)


def check_orchestrator_process(config: OllamaConfig) -> bool:
    step("Step 4: OllamaOrchestrator.process() with OrchestratorContext")
    try:
        orchestrator = OllamaOrchestrator(config=config)
        context = OrchestratorContext(
            event={
                "event_id": "smoke-test-001",
                "type": "USER_MESSAGE",
                "source": "smoke_test",
                "timestamp": "2026-08-27T00:00:00Z",
                "data": {"text": "ping"},
            },
            system_context={"runtime": {"plugins": {}}},
        )
        result = orchestrator.process(context)
        if not isinstance(result, OrchestratorResult):
            raise TypeError(f"Expected OrchestratorResult, got {type(result).__name__}")
        print(f"  Result status={result.status}, complete={result.complete}, decision={result.decision}")
        if result.status == "ERROR":
            err = result.error or {}
            print(f"  Orchestrator error: {err.get('code')}: {err.get('message')}")
            return report("OllamaOrchestrator.process() returned a result", False, RuntimeError("Orchestrator returned ERROR"))
        return report("OllamaOrchestrator.process() returned a result", True)
    except Exception as exc:
        return report("OllamaOrchestrator.process() returned a result", False, exc)


def check_full_runtime(config: OllamaConfig) -> bool:
    step("Step 5: Full NexusRuntime with LocalOrchestrator and USER_MESSAGE event")
    try:
        registry = PluginRegistry()

        # Register a fake plugin that always succeeds
        def fake_entry(payload: dict[str, Any]) -> dict[str, Any]:
            return {"status": "SUCCESS", "data": {"echo": payload.get("data", {})}, "message": "ok"}

        registry.register("fake", fake_entry, {"ECHO", "PING"})

        orchestrator = _CompleteAfterFirstCallOrchestrator(LocalOrchestrator(config=config))
        runtime = NexusRuntime(plugin_registry=registry, orchestrator=orchestrator)
        print("  Note: forcing cycle completion after first orchestrator call to avoid CPU-only timeout.")
        try:
            result = runtime.submit_event(
                {
                    "type": "USER_MESSAGE",
                    "source": "smoke_test",
                    "data": {"text": "ping"},
                },
                timeout=config.timeout_seconds,
            )
            print(f"  Runtime result status={result.get('status')}, termination_reason={result.get('termination_reason')}")
            if result.get("status") == "ERROR":
                print(f"  Runtime error details: {result.get('orchestrator_result', {}).get('error')}")
                return report("NexusRuntime processed USER_MESSAGE", False, RuntimeError("Runtime returned ERROR status"))
            return report("NexusRuntime processed USER_MESSAGE", True)
        finally:
            runtime.stop()
    except Exception as exc:
        return report("NexusRuntime processed USER_MESSAGE", False, exc)


def main() -> int:
    print("Nexus Ollama Smoke Test")
    print("=" * 40)

    config = OllamaConfig.from_environment()
    print(f"  base_url     = {config.base_url}")
    print(f"  model        = {config.model}")
    print(f"  timeout      = {config.timeout_seconds}s")
    print(f"  max_retries  = {config.max_retries}")

    results: list[bool] = []
    results.append(check_ollama_reachable(config.base_url))
    results.append(check_model_exists(config))
    results.append(check_direct_chat_request(config))
    results.append(check_orchestrator_process(config))
    results.append(check_full_runtime(config))

    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} steps passed")
    if all(results):
        print("All smoke tests PASSED")
        return 0
    print("Some smoke tests FAILED")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        print(f"\nUnexpected error: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        sys.exit(1)
