from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from orchestrators import Orchestrator, OrchestratorContext, OrchestratorResult, ResponseRequest

from .router import PluginRouter
from .validator import ExecutionPlanValidator, ValidationResult


@dataclass(frozen=True)
class OrchestrationCycleConfig:
    max_iterations: int = 5
    repeated_plan_limit: int = 2
    max_history_entries: int = 50


class OrchestrationCycle:
    """Run one bounded event-specific orchestration cycle."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        validator: ExecutionPlanValidator,
        router: PluginRouter,
        config: OrchestrationCycleConfig | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.validator = validator
        self.router = router
        self.config = config or OrchestrationCycleConfig()
        if self.config.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")
        if self.config.repeated_plan_limit < 1:
            raise ValueError("repeated_plan_limit must be at least 1.")
        if self.config.max_history_entries < 1:
            raise ValueError("max_history_entries must be at least 1.")

    def run(self, initial_context: OrchestratorContext) -> dict[str, Any]:
        working_context = dict(initial_context.working_context)
        history: list[dict[str, Any]] = []
        last_fingerprint: str | None = None
        repeated_plans = 0
        final_response: dict[str, Any] = {"required": False, "text": ""}
        termination_reason = "LIMIT_REACHED"
        status = "LIMIT_REACHED"
        had_validation_errors = False
        iterations = 0

        for iteration in range(1, self.config.max_iterations + 1):
            iterations = iteration
            context = OrchestratorContext(
                event=initial_context.event,
                user_context=initial_context.user_context,
                memories=initial_context.memories,
                working_context={**working_context, "execution_history": list(history)},
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

            successful_action_ids = {
                item["action_id"]
                for entry in history
                for item in entry["execution_results"]
                if item.get("status") == "SUCCESS" and item.get("action_id")
            }
            validation = self.validator.validate(orchestrator_result, successful_action_ids)
            had_validation_errors = had_validation_errors or bool(validation.errors)
            fingerprint = self._plan_fingerprint(orchestrator_result)
            if fingerprint == last_fingerprint:
                repeated_plans += 1
            else:
                repeated_plans = 1
                last_fingerprint = fingerprint

            execution_results = self.router.execute(validation.approved_plan or [], successful_action_ids)
            execution_results = self._with_validation_errors(execution_results, validation)
            history_entry = {
                "iteration": iteration,
                "orchestrator_result": orchestrator_result.to_dict(),
                "validation_result": validation.to_dict(),
                "execution_results": execution_results,
            }
            history.append(history_entry)
            if len(history) > self.config.max_history_entries:
                history = history[-self.config.max_history_entries:]

            final_response = orchestrator_result.response.to_dict() if hasattr(orchestrator_result.response, "to_dict") else dict(orchestrator_result.response)
            working_context["execution_history"] = list(history)
            working_context["last_execution_results"] = execution_results

            if orchestrator_result.complete:
                termination_reason = "COMPLETED"
                status = "PARTIAL_SUCCESS" if had_validation_errors else "SUCCESS"
                break
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
