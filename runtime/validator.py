from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orchestrators import ActionRequest, OrchestratorResult
from .registry import PluginRegistry


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    action_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.action_id is not None:
            result["action_id"] = self.action_id
        return result


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    approved_plan: list[ActionRequest] | None
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "approved_plan": [action.to_dict() for action in self.approved_plan] if self.approved_plan is not None else None,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


class ExecutionPlanValidator:
    """Validates structure and plugin references without applying policy decisions."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    def validate(
        self,
        result: OrchestratorResult | dict[str, Any],
        known_action_ids: set[str] | None = None,
    ) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        actions = result.actions if isinstance(result, OrchestratorResult) else result.get("actions", [])

        if not isinstance(actions, list):
            return ValidationResult(False, None, [ValidationIssue("INVALID_ACTIONS", "actions must be a list.")])

        approved: list[ActionRequest] = []
        seen: set[str] = set()
        all_ids = set(known_action_ids or ())
        all_ids.update(str(item.get("action_id")) for item in actions if isinstance(item, dict) and item.get("action_id"))

        for raw_action in actions:
            if isinstance(raw_action, ActionRequest):
                action = raw_action
            elif isinstance(raw_action, dict):
                if not isinstance(raw_action.get("data", {}), dict):
                    errors.append(ValidationIssue("INVALID_ACTION_DATA", "Action data must be a dictionary.", str(raw_action.get("action_id")) if raw_action.get("action_id") else None))
                    continue
                if not isinstance(raw_action.get("depends_on", []), list):
                    errors.append(ValidationIssue("INVALID_DEPENDENCIES", "depends_on must be a list.", str(raw_action.get("action_id")) if raw_action.get("action_id") else None))
                    continue
                try:
                    action = ActionRequest.from_dict(raw_action)
                except (TypeError, ValueError):
                    errors.append(ValidationIssue("MALFORMED_ACTION", "Action must contain valid fields.", None))
                    continue
            else:
                errors.append(ValidationIssue("MALFORMED_ACTION", "Each action must be an object.", None))
                continue

            action_id = action.action_id
            if not action.plugin.strip() or not action.action.strip():
                errors.append(ValidationIssue("MISSING_FIELD", "Action plugin and action are required.", action_id))
                continue
            if action_id in seen:
                errors.append(ValidationIssue("DUPLICATE_ACTION_ID", "Action IDs must be unique.", action_id))
                continue
            seen.add(action_id)
            if not isinstance(action.data, dict):
                errors.append(ValidationIssue("INVALID_ACTION_DATA", "Action data must be a dictionary.", action_id))
                continue
            plugin = self.registry.get(action.plugin)
            if plugin is None:
                errors.append(ValidationIssue("PLUGIN_NOT_FOUND", f"Plugin is not registered: {action.plugin}.", action_id))
                continue
            if action.action.upper() not in plugin.actions:
                errors.append(ValidationIssue("ACTION_NOT_SUPPORTED", f"Plugin {action.plugin} does not support {action.action}.", action_id))
                continue
            missing_dependencies = [dependency for dependency in action.depends_on if dependency not in all_ids]
            if missing_dependencies:
                errors.append(ValidationIssue("INVALID_DEPENDENCY", f"Unknown dependencies: {', '.join(missing_dependencies)}.", action_id))
                continue
            approved.append(action)

        approved_ids = {action.action_id for action in approved}
        known_ids = set(known_action_ids or ())
        dependency_safe: list[ActionRequest] = []
        for action in approved:
            if any(dependency not in approved_ids and dependency not in known_ids for dependency in action.depends_on):
                errors.append(ValidationIssue("DEPENDENCY_REJECTED", "A dependency was rejected from the approved plan.", action.action_id))
                approved_ids.discard(action.action_id)
                continue
            dependency_safe.append(action)
        approved = dependency_safe

        valid = not errors
        if errors and approved:
            warnings.append(ValidationIssue("PARTIAL_PLAN", "Some invalid actions were excluded; valid actions remain available."))
        return ValidationResult(valid, approved, errors, warnings)
