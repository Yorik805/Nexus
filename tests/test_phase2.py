from __future__ import annotations

from orchestrators import ActionRequest, DummyOrchestrator, OrchestratorContext, OrchestratorResult
from orchestrators.prompt_loader import build_orchestrator_request, build_system_instruction
from runtime import ContextBuilder, Event, ExecutionPlanValidator, NexusRuntime, PluginRegistry, PluginRouter


def make_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("fake", lambda request: {"status": "SUCCESS", "message": "ok", "data": request["data"]}, {"ECHO"})
    registry.register("broken", lambda request: (_ for _ in ()).throw(RuntimeError("boom")), {"FAIL"})
    registry.register("malformed", lambda request: {"not": "a plugin response"}, {"BAD"})
    return registry


def test_dummy_implements_replaceable_orchestrator_contract() -> None:
    context = OrchestratorContext(
        event={"event_id": "evt", "type": "SYSTEM_EVENT", "source": "test", "data": {}},
        system_context={"device": "laptop"},
    )
    result = DummyOrchestrator().process(context)
    assert isinstance(result, OrchestratorResult)
    assert result.response.required is True
    assert result.actions == []


def test_registry_discovers_existing_plugin_actions() -> None:
    registry = PluginRegistry()
    assert {"READ", "WRITE", "EXISTS"}.issubset(registry.get("filesystem").actions)
    assert {"SEARCH", "WRITE", "GET"}.issubset(registry.get("memory").actions)
    assert "EXECUTE" in registry.get("terminal").actions
    assert registry.metadata()["filesystem"]["actions"]
    search_contract = registry.metadata()["memory"]["contracts"]["SEARCH"]
    assert "type" in search_contract["required"]
    assert search_contract["required"]["type"]["enum"] == ["SQLITE", "VECTOR"]
    write_contract = registry.metadata()["memory"]["contracts"]["WRITE"]
    assert {"title", "category", "content"}.issubset(write_contract["required"])
    assert "tags" in write_contract.get("optional", {})


def test_validator_enforces_action_contract_fields_and_enums() -> None:
    validator = ExecutionPlanValidator(PluginRegistry())
    missing = validator.validate({"actions": [{"action_id": "search", "plugin": "memory", "action": "SEARCH", "data": {"query": "x"}}]})
    invalid = validator.validate({"actions": [{"action_id": "search", "plugin": "memory", "action": "SEARCH", "data": {"type": "BAD", "query": "x"}}]})
    assert {issue.code for issue in missing.errors} == {"MISSING_ACTION_FIELD"}
    assert {issue.code for issue in invalid.errors} == {"INVALID_ACTION_FIELD"}


def test_context_builder_retrieves_memory_before_orchestrator() -> None:
    registry = PluginRegistry()
    calls: list[dict] = []
    registry.register("memory", lambda request: calls.append(request) or {"status": "SUCCESS", "data": {"results": [{"title": "Nexus"}]}}, {"SEARCH"})
    context = ContextBuilder(registry).build(Event(type="USER_MESSAGE", data={"text": "Nexus architecture"}))
    assert calls[0]["data"]["type"] == "SQLITE"
    assert context["memories"] == [{"title": "Nexus"}]
    assert context["system_context"]["context_metadata"]["memory"]["status"] == "success"


def test_non_user_event_does_not_retrieve_memory() -> None:
    calls: list[str] = []
    builder = ContextBuilder(memory_retriever=lambda text: calls.append(text) or [{"title": "unexpected"}])
    context = builder.build(Event(type="EXECUTION_RESULT", data={"status": "SUCCESS"}))
    assert calls == []
    assert context["memories"] == []
    assert context["system_context"]["context_metadata"]["memory"]["status"] == "not_applicable"


def test_memory_retrieval_failure_is_recorded_without_crashing() -> None:
    builder = ContextBuilder(memory_retriever=lambda _text: (_ for _ in ()).throw(RuntimeError("memory offline")))
    context = builder.build(Event(type="USER_MESSAGE", data={"text": "hello"}))
    memory_metadata = context["system_context"]["context_metadata"]["memory"]
    assert context["memories"] == []
    assert memory_metadata["status"] == "failed"
    assert "memory offline" in memory_metadata["error"]


def test_empty_memory_retrieval_is_distinguished_from_failure() -> None:
    context = ContextBuilder(memory_retriever=lambda _text: []).build(Event(type="USER_MESSAGE", data={"text": "unknown"}))
    assert context["system_context"]["context_metadata"]["memory"]["status"] == "empty"


def test_runtime_exposes_explicit_memory_contract_without_delegating_context_retrieval() -> None:
    runtime = NexusRuntime()
    context = runtime.context_builder.build(Event(type="SYSTEM_EVENT", data={}))
    runtime_context = runtime.registry.metadata()
    assert "SEARCH" in runtime_context["memory"]["actions"]
    assert "type" in runtime_context["memory"]["contracts"]["SEARCH"]["required"]
    assert context["memories"] == []


def test_validator_accepts_valid_plan_and_rejects_invalid_entries_partially() -> None:
    validator = ExecutionPlanValidator(make_registry())
    result = validator.validate({
        "actions": [
            {"action_id": "valid", "plugin": "fake", "action": "ECHO", "data": {"value": 1}},
            {"action_id": "missing", "plugin": "unknown", "action": "ECHO", "data": {}},
            {"action_id": "bad-action", "plugin": "fake", "action": "NOPE", "data": {}},
            {"action_id": "valid", "plugin": "fake", "action": "ECHO", "data": {}},
        ]
    })
    assert result.valid is False
    assert [action.action_id for action in result.approved_plan] == ["valid"]
    assert {issue.code for issue in result.errors} == {"PLUGIN_NOT_FOUND", "ACTION_NOT_SUPPORTED", "DUPLICATE_ACTION_ID"}
    assert result.warnings[0].code == "PARTIAL_PLAN"


def test_validator_rejects_missing_fields_data_and_dependencies() -> None:
    validator = ExecutionPlanValidator(make_registry())
    result = validator.validate({
        "actions": [
            {"action_id": "missing-plugin", "action": "ECHO", "data": {}},
            {"action_id": "bad-data", "plugin": "fake", "action": "ECHO", "data": None},
            {"action_id": "bad-dependency", "plugin": "fake", "action": "ECHO", "data": {}, "depends_on": ["nope"]},
        ]
    })
    assert result.valid is False
    assert result.approved_plan == []
    assert {issue.code for issue in result.errors} == {"MISSING_FIELD", "INVALID_ACTION_DATA", "INVALID_DEPENDENCY"}


def test_router_executes_sequentially_and_isolates_errors() -> None:
    registry = make_registry()
    router = PluginRouter(registry)
    results = router.execute([
        ActionRequest(action_id="one", plugin="fake", action="ECHO", data={"step": 1}),
        ActionRequest(action_id="two", plugin="fake", action="ECHO", data={"step": 2}, depends_on=["one"]),
        ActionRequest(action_id="three", plugin="broken", action="FAIL"),
        ActionRequest(action_id="four", plugin="malformed", action="BAD"),
        ActionRequest(action_id="five", plugin="fake", action="ECHO", data={"step": 5}),
    ])
    assert [result["status"] for result in results] == ["SUCCESS", "SUCCESS", "ERROR", "ERROR", "SUCCESS"]
    assert results[1]["result"] == {"step": 2}
    assert results[2]["action_id"] == "three"
    assert results[4]["action_id"] == "five"


def test_runtime_executes_explicit_dummy_action() -> None:
    registry = make_registry()
    runtime = NexusRuntime(registry, DummyOrchestrator([
        {"action_id": "echo", "plugin": "fake", "action": "ECHO", "data": {"hello": "world"}},
    ]))
    runtime.start()
    try:
        result = runtime.submit_event({"type": "USER_MESSAGE", "source": "test", "data": {"text": "run"}})
    finally:
        runtime.stop()
    assert result["status"] == "SUCCESS"
    assert result["validation_result"]["valid"] is True
    assert result["execution_results"][0]["result"] == {"hello": "world"}


def test_prompt_loader_composes_versioned_instructions_and_runtime_data() -> None:
    prompt = build_system_instruction({"plugins": {"fake": ["ECHO"]}, "device": "laptop"})
    assert "AI operating system orchestrator" in prompt
    assert '"ECHO"' in prompt
    assert "available plugin metadata" in prompt


def test_orchestrator_request_keeps_runtime_metadata_out_of_system_context() -> None:
    runtime_info = {"plugins": {"fake": {"actions": ["ECHO"]}}}
    context = OrchestratorContext(
        event={"event_id": "evt", "type": "SYSTEM_EVENT", "source": "test", "data": {}},
        system_context={"runtime": runtime_info, "runtime_state": runtime_info, "device": "laptop"},
    )

    request = build_orchestrator_request(context)

    assert request.context["runtime"] == runtime_info
    assert request.context["system_context"] == {"device": "laptop"}
