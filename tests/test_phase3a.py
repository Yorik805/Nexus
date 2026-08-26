from __future__ import annotations

from orchestrators import ActionRequest, Orchestrator, OrchestratorContext, OrchestratorResult, ResponseRequest
from runtime import (
    ExecutionPlanValidator,
    OrchestrationCycle,
    OrchestrationCycleConfig,
    PluginRegistry,
    PluginRouter,
    NexusRuntime,
)


class SequenceOrchestrator(Orchestrator):
    def __init__(self, steps: list[list[ActionRequest]]) -> None:
        self.steps = steps
        self.calls: list[OrchestratorContext] = []

    def process(self, context: OrchestratorContext) -> OrchestratorResult:
        self.calls.append(context)
        iteration = len(self.calls) - 1
        complete = iteration >= len(self.steps)
        actions = self.steps[iteration] if iteration < len(self.steps) else []
        return OrchestratorResult(
            complete=complete,
            actions=actions,
            response=ResponseRequest(required=complete, text="Task completed." if complete else ""),
        )


def make_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("fake", lambda request: {"status": "SUCCESS", "message": "ok", "data": request["data"]}, {"ECHO"})
    registry.register("failure", lambda request: {"status": "ERROR", "message": "missing", "data": {}}, {"FAIL"})
    return registry


def make_cycle(orchestrator: Orchestrator, config: OrchestrationCycleConfig | None = None) -> OrchestrationCycle:
    registry = make_registry()
    return OrchestrationCycle(
        orchestrator,
        ExecutionPlanValidator(registry),
        PluginRouter(registry),
        config,
    )


def initial_context() -> OrchestratorContext:
    return OrchestratorContext(
        event={"event_id": "event-1", "type": "USER_MESSAGE", "source": "test", "data": {"text": "go"}},
    )


def test_two_step_cycle_passes_results_to_next_context() -> None:
    orchestrator = SequenceOrchestrator([
        [ActionRequest(action_id="a", plugin="fake", action="ECHO", data={"step": 1})],
        [ActionRequest(action_id="b", plugin="fake", action="ECHO", data={"step": 2}, depends_on=["a"])],
    ])
    result = make_cycle(orchestrator).run(initial_context())

    assert result["status"] == "SUCCESS"
    assert result["termination_reason"] == "COMPLETED"
    assert result["iterations"] == 3
    assert len(result["history"]) == 3
    assert orchestrator.calls[1].working_context["execution_history"][0]["execution_results"][0]["action_id"] == "a"
    assert orchestrator.calls[2].working_context["execution_history"][1]["execution_results"][0]["action_id"] == "b"
    assert result["response"]["text"] == "Task completed."


def test_context_builder_is_used_on_every_iteration() -> None:
    calls: list[tuple[dict, list[dict]]] = []

    def build(event, *, execution_state, execution_history, runtime_state):
        calls.append((event, execution_history))
        return {"event": event, "working_context": {}, "memories": [], "user_context": {}, "active_tasks": [], "system_context": {}}

    orchestrator = SequenceOrchestrator([
        [ActionRequest(action_id="a", plugin="fake", action="ECHO")],
    ])
    cycle = OrchestrationCycle(
        orchestrator,
        ExecutionPlanValidator(make_registry()),
        PluginRouter(make_registry()),
        context_builder=build,
    )
    result = cycle.run(initial_context())
    assert result["termination_reason"] == "COMPLETED"
    assert len(calls) == result["iterations"]
    assert calls[1][1][0]["execution_results"][0]["action_id"] == "a"


def test_no_action_is_a_valid_idle_outcome() -> None:
    class IdleOrchestrator(Orchestrator):
        def process(self, context: OrchestratorContext) -> OrchestratorResult:
            return OrchestratorResult(complete=False, decision="NO_ACTION", response=ResponseRequest(required=False, text="idle"))

    result = make_cycle(IdleOrchestrator()).run(initial_context())
    assert result["status"] == "IDLE"
    assert result["termination_reason"] == "NO_ACTION"
    assert result["execution_results"] == []


def test_history_manager_compresses_old_records_and_preserves_failures() -> None:
    from runtime import ContextHistoryManager

    manager = ContextHistoryManager(recent_limit=2)
    for index, status in enumerate(["SUCCESS", "ERROR", "SUCCESS", "ERROR"]):
        manager.append({"iteration": index, "execution_results": [{"action_id": f"a{index}", "status": status, "message": "important"}]})
    context = manager.context()
    assert len(context["recent_execution_history"]) == 2
    assert "a0=SUCCESS" in context["historical_summary"]
    assert "a1=ERROR" in context["historical_summary"]
    assert context["compression"]["occurred"] is True


def test_same_plan_dependency_chain_executes_in_dependency_order() -> None:
    orchestrator = SequenceOrchestrator([[
        ActionRequest(action_id="read", plugin="fake", action="ECHO", data={"step": 2}, depends_on=["write"]),
        ActionRequest(action_id="write", plugin="fake", action="ECHO", data={"step": 1}),
    ]])
    result = make_cycle(orchestrator).run(initial_context())
    assert [item["action_id"] for item in result["history"][0]["execution_results"]] == ["write", "read"]
    assert result["status"] == "SUCCESS"


def test_failed_dependency_prevents_completion_even_when_orchestrator_says_complete() -> None:
    class CompleteAfterFailure(Orchestrator):
        def process(self, context: OrchestratorContext) -> OrchestratorResult:
            return OrchestratorResult(
                status="SUCCESS", complete=True,
                actions=[ActionRequest(action_id="read", plugin="failure", action="FAIL", depends_on=["missing"])],
                response=ResponseRequest(required=True, text="verified"),
            )

    result = make_cycle(CompleteAfterFailure()).run(initial_context())
    assert result["termination_reason"] != "COMPLETED"
    assert result["status"] != "SUCCESS"


def test_three_step_cycle_accumulates_history() -> None:
    orchestrator = SequenceOrchestrator([
        [ActionRequest(action_id="one", plugin="fake", action="ECHO", data={"n": 1})],
        [ActionRequest(action_id="two", plugin="fake", action="ECHO", data={"n": 2})],
        [ActionRequest(action_id="three", plugin="fake", action="ECHO", data={"n": 3})],
    ])
    result = make_cycle(orchestrator).run(initial_context())

    assert result["iterations"] == 4
    assert [entry["iteration"] for entry in result["history"]] == [1, 2, 3, 4]
    assert [entry["execution_results"][0]["action_id"] for entry in result["history"][:3]] == ["one", "two", "three"]


def test_plugin_failure_is_returned_and_cycle_continues() -> None:
    orchestrator = SequenceOrchestrator([
        [ActionRequest(action_id="failed", plugin="failure", action="FAIL")],
        [],
    ])
    result = make_cycle(orchestrator).run(initial_context())

    assert result["status"] == "NO_PROGRESS"
    assert result["termination_reason"] == "NO_PROGRESS"
    assert result["history"][0]["execution_results"][0]["status"] == "ERROR"
    assert len(orchestrator.calls[1].working_context["execution_history"]) == 1


def test_invalid_action_is_recorded_while_valid_action_executes() -> None:
    orchestrator = SequenceOrchestrator([[
        ActionRequest(action_id="valid", plugin="fake", action="ECHO", data={"ok": True}),
        ActionRequest(action_id="invalid", plugin="missing", action="NOPE", data={}),
    ]])
    result = make_cycle(orchestrator).run(initial_context())

    assert result["status"] == "NO_PROGRESS"
    execution_results = result["history"][0]["execution_results"]
    assert any(item["action_id"] == "invalid" and item["phase"] == "VALIDATION" for item in execution_results)
    assert any(item["action_id"] == "valid" and item["status"] == "SUCCESS" for item in execution_results)


def test_maximum_iteration_limit_is_structured() -> None:
    orchestrator = SequenceOrchestrator([
        [ActionRequest(action_id="one", plugin="fake", action="ECHO", data={"n": 1})],
        [ActionRequest(action_id="two", plugin="fake", action="ECHO", data={"n": 2})],
    ])
    result = make_cycle(orchestrator, OrchestrationCycleConfig(max_iterations=2, repeated_plan_limit=10)).run(initial_context())

    assert result["status"] == "LIMIT_REACHED"
    assert result["termination_reason"] == "LIMIT_REACHED"
    assert result["iterations"] == 2


def test_repeated_plan_stops_as_no_progress() -> None:
    action = ActionRequest(action_id="same", plugin="fake", action="ECHO", data={"same": True})
    orchestrator = SequenceOrchestrator([[action], [action], [action]])
    result = make_cycle(orchestrator, OrchestrationCycleConfig(max_iterations=5, repeated_plan_limit=2)).run(initial_context())

    assert result["status"] == "NO_PROGRESS"
    assert result["termination_reason"] == "NO_PROGRESS"
    assert result["iterations"] == 2


def test_orchestrator_failure_is_not_reported_as_success() -> None:
    class FailingOrchestrator(Orchestrator):
        def process(self, context: OrchestratorContext) -> OrchestratorResult:
            return OrchestratorResult(
                status="ERROR",
                complete=True,
                response=ResponseRequest(required=False, text=""),
                error={"code": "UNAVAILABLE", "message": "provider unavailable"},
            )

    result = make_cycle(FailingOrchestrator()).run(initial_context())
    assert result["status"] == "ERROR"
    assert result["termination_reason"] == "ORCHESTRATOR_ERROR"
    assert result["orchestrator_result"]["error"]["code"] == "UNAVAILABLE"


def test_runtime_stays_alive_and_processes_independent_events() -> None:
    runtime = NexusRuntime(make_registry(), SequenceOrchestrator([
        [ActionRequest(action_id="event-action", plugin="fake", action="ECHO", data={"ok": True})],
    ]))
    runtime.start()
    try:
        first = runtime.submit_event({"type": "USER_MESSAGE", "source": "one", "data": {"text": "one"}})
        second = runtime.submit_event({"type": "USER_MESSAGE", "source": "two", "data": {"text": "two"}})
        assert first["termination_reason"] == "COMPLETED"
        assert second["termination_reason"] == "COMPLETED"
        assert runtime.is_running is True
    finally:
        runtime.stop()
