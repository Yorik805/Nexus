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

    assert result["status"] == "SUCCESS"
    assert result["termination_reason"] == "COMPLETED"
    assert result["history"][0]["execution_results"][0]["status"] == "ERROR"
    assert len(orchestrator.calls[1].working_context["execution_history"]) == 1


def test_invalid_action_is_recorded_while_valid_action_executes() -> None:
    orchestrator = SequenceOrchestrator([[
        ActionRequest(action_id="valid", plugin="fake", action="ECHO", data={"ok": True}),
        ActionRequest(action_id="invalid", plugin="missing", action="NOPE", data={}),
    ]])
    result = make_cycle(orchestrator).run(initial_context())

    assert result["status"] == "PARTIAL_SUCCESS"
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
