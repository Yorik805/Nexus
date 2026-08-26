from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from orchestrators import Orchestrator, OrchestratorContext, OrchestratorResult, ResponseRequest

from .router import PluginRouter
from .validator import ExecutionPlanValidator, ValidationResult
from .history import ContextHistoryManager
from .observability import RuntimeTrace


@dataclass(frozen=True)
class OrchestrationCycleConfig:
    max_iterations: int = 20
    repeated_plan_limit: int = 2
    max_history_entries: int = 50
    recent_history_limit: int = 20
    emergency_iteration_limit: int = 20


class OrchestrationCycle:
    """Run one bounded event-specific orchestration cycle."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        validator: ExecutionPlanValidator,
        router: PluginRouter,
        config: OrchestrationCycleConfig | None = None,
        context_builder: Callable[..., dict[str, Any]] | None = None,
        trace: RuntimeTrace | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.validator = validator
        self.router = router
        self.config = config or OrchestrationCycleConfig()
        self.context_builder = context_builder
        self.trace = trace
        if self.config.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")
        if self.config.repeated_plan_limit < 1:
            raise ValueError("repeated_plan_limit must be at least 1.")
        if self.config.max_history_entries < 1:
            raise ValueError("max_history_entries must be at least 1.")
        if self.config.recent_history_limit < 1 or self.config.emergency_iteration_limit < 1:
            raise ValueError("history and emergency limits must be at least 1.")

    def run(self, initial_context: OrchestratorContext) -> dict[str, Any]:
        working_context = dict(initial_context.working_context)
        history: list[dict[str, Any]] = []
        history_manager = ContextHistoryManager(self.config.recent_history_limit)
        last_fingerprint: str | None = None
        repeated_plans = 0
        final_response: dict[str, Any] = {"required": False, "text": ""}
        termination_reason = "LIMIT_REACHED"
        status = "LIMIT_REACHED"
        had_validation_errors = False
        iterations = 0
        failed_action_ids: set[str] = set()

        for iteration in range(1, min(self.config.max_iterations, self.config.emergency_iteration_limit) + 1):
            iterations = iteration
            if self.trace:
                self.trace.record("iteration.start", initial_context.event.get("event_id"), iteration=iteration, history_count=len(history_manager.records()))
            if self.context_builder is not None:
                built = self.context_builder(
                    initial_context.event,
                    execution_state=working_context,
                    execution_history=history_manager.records(),
                    runtime_state=initial_context.system_context.get("runtime", {}),
                )
                context = OrchestratorContext(
                    event=built["event"],
                    user_context=built.get("user_context", {}),
                    memories=built.get("memories", []),
                    working_context={**built.get("working_context", {}), **working_context, "execution_history": history_manager.records(), "history_context": history_manager.context()},
                    active_tasks=built.get("active_tasks", []),
                    system_context={**initial_context.system_context, **built.get("system_context", {})},
                )
            else:
                context = OrchestratorContext(
                    event=initial_context.event,
                    user_context=initial_context.user_context,
                    memories=initial_context.memories,
                    working_context={**working_context, "execution_history": history_manager.records(), "history_context": history_manager.context()},
                    active_tasks=initial_context.active_tasks,
                    system_context=initial_context.system_context,
                )
            try:
                orchestrator_result = self.orchestrator.process(context)
            except Exception as exc:
                orchestrator_result = OrchestratorResult(
                    status="ERROR",
                    complete=True,
                    response=ResponseRequest(required=True, text=""),
                    metadata={"error": str(exc)},
                    error={"code": "ORCHESTRATOR_ERROR", "message": str(exc)},
                )
            if self.trace:
                self.trace.record("orchestrator.decision", initial_context.event.get("event_id"), iteration=iteration, decision=orchestrator_result.decision, complete=orchestrator_result.complete, action_count=len(orchestrator_result.actions))

            successful_action_ids = {
                item["action_id"]
                for entry in history
                for item in entry["execution_results"]
                if item.get("status") == "SUCCESS" and item.get("action_id")
            }
            validation = self.validator.validate(orchestrator_result, successful_action_ids)
            if self.trace:
                self.trace.record("validator.complete", initial_context.event.get("event_id"), iteration=iteration, valid=validation.valid, approved_count=len(validation.approved_plan or []), error_count=len(validation.errors), error_codes=[issue.code for issue in validation.errors], error_messages=[issue.message for issue in validation.errors])
            had_validation_errors = had_validation_errors or bool(validation.errors)
            fingerprint = self._plan_fingerprint(orchestrator_result)
            if fingerprint == last_fingerprint:
                repeated_plans += 1
            else:
                repeated_plans = 1
                last_fingerprint = fingerprint

            execution_results = self.router.execute(validation.approved_plan or [], successful_action_ids, self.trace)
            execution_results = self._with_validation_errors(execution_results, validation)
            for item in execution_results:
                action_id = item.get("action_id")
                if action_id and item.get("status") == "ERROR":
                    failed_action_ids.add(action_id)
                elif action_id and item.get("status") == "SUCCESS":
                    failed_action_ids.discard(action_id)
            history_entry = {
                "iteration": iteration,
                "orchestrator_result": orchestrator_result.to_dict(),
                "validation_result": validation.to_dict(),
                "execution_results": execution_results,
            }
            history_manager.append(history_entry)
            history = history_manager.records()

            final_response = orchestrator_result.response.to_dict() if hasattr(orchestrator_result.response, "to_dict") else dict(orchestrator_result.response)
            working_context["execution_history"] = history_manager.context()
            working_context["history_context"] = history_manager.context()
            working_context["last_execution_results"] = execution_results
            if self.trace:
                self.trace.record("history.updated", initial_context.event.get("event_id"), iteration=iteration, recent_count=len(history_manager.records()), compressed=history_manager.context()["compression"]["occurred"], result_count=len(execution_results))

            decision = orchestrator_result.decision.upper()
            if orchestrator_result.status == "ERROR" or orchestrator_result.error:
                termination_reason = "ORCHESTRATOR_ERROR"
                status = "ERROR"
                break
            if decision == "NO_ACTION":
                if self.trace:
                    self.trace.record("cycle.idle", initial_context.event.get("event_id"), iteration=iteration)
                termination_reason = "NO_ACTION"
                status = "IDLE"
                break
            if (decision == "COMPLETE" or orchestrator_result.complete) and not failed_action_ids and not validation.errors:
                termination_reason = "COMPLETED"
                if orchestrator_result.status != "SUCCESS":
                    status = orchestrator_result.status
                else:
                    status = "PARTIAL_SUCCESS" if had_validation_errors else "SUCCESS"
                break
            if decision == "COMPLETE" or orchestrator_result.complete:
                final_response = {"required": True, "text": "The requested actions have not completed successfully.", "metadata": {}}
            if repeated_plans >= self.config.repeated_plan_limit:
                termination_reason = "NO_PROGRESS"
                status = "NO_PROGRESS"
                break
        else:
            termination_reason = "LIMIT_REACHED"
            status = "LIMIT_REACHED"

        latest = history[-1] if history else {
            "orchestrator_result": {},
            "validation_result": {},
            "execution_results": [],
        }
        return {
            "event_id": initial_context.event.get("event_id"),
            "status": status,
            "termination_reason": termination_reason,
            "iterations": iterations,
            "history": history,
            "orchestrator_result": latest["orchestrator_result"],
            "validation_result": latest["validation_result"],
            "execution_results": latest["execution_results"],
            "response": final_response,
        }

    @staticmethod
    def _plan_fingerprint(result: OrchestratorResult) -> str:
        actions = [action.to_dict() if hasattr(action, "to_dict") else action for action in result.actions]
        return json.dumps(actions, sort_keys=True, default=str)

    @staticmethod
    def _with_validation_errors(
        execution_results: list[dict[str, Any]],
        validation: ValidationResult,
    ) -> list[dict[str, Any]]:
        validation_results = [
            {
                "action_id": issue.action_id,
                "plugin": None,
                "action": None,
                "status": "ERROR",
                "result": {},
                "message": issue.message,
                "phase": "VALIDATION",
                "code": issue.code,
            }
            for issue in validation.errors
        ]
        return validation_results + execution_results
