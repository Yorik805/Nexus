from __future__ import annotations

from typing import Any

from orchestrators import ActionRequest
from .registry import PluginRegistry
from .observability import RuntimeTrace


class PluginRouter:
    """Executes approved plugin actions in declared sequential order."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        actions: list[ActionRequest] | None,
        successful_action_ids: set[str] | None = None,
        trace: RuntimeTrace | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        successful_ids = set(successful_action_ids or ())
        pending = list(actions or [])
        while pending:
            progress = False
            deferred: list[ActionRequest] = []
            for action in pending:
                if action.action.upper() == "NO_ACTION":
                    results.append({"action_id": action.action_id, "plugin": None, "action": "NO_ACTION", "status": "SUCCESS", "result": {}, "message": "No action requested."})
                    if trace:
                        trace.record("decision.no_action", None, action_id=action.action_id)
                    progress = True
                    continue
                unresolved = [dependency for dependency in action.depends_on if dependency not in successful_ids]
                pending_ids = {item.action_id for item in pending}
                if unresolved and any(dependency in pending_ids for dependency in unresolved):
                    deferred.append(action)
                    continue
                progress = True
                pending_ids.discard(action.action_id)
                base = {"action_id": action.action_id, "plugin": action.plugin, "action": action.action}
                blocked = [dependency for dependency in action.depends_on if dependency not in successful_ids]
                if blocked:
                    results.append({**base, "status": "ERROR", "result": {}, "message": f"Dependencies did not succeed: {', '.join(blocked)}"})
                    continue
                plugin = self.registry.get(action.plugin)
                if plugin is None:
                    results.append({**base, "status": "ERROR", "result": {}, "message": f"Plugin is not registered: {action.plugin}"})
                    continue
                try:
                    response = plugin.entry_point({"action": action.action.upper(), "data": action.data})
                    if not isinstance(response, dict) or response.get("status") not in {"SUCCESS", "ERROR"} or not isinstance(response.get("data", {}), dict):
                        response = {"status": "ERROR", "data": {}, "message": "Plugin returned a malformed response."}
                    execution = {**base, "status": response["status"], "result": response.get("data", {}), "message": response.get("message", "")}
                except Exception as exc:
                    execution = {**base, "status": "ERROR", "result": {}, "message": f"Plugin execution failed: {exc}"}
                results.append(execution)
                if trace:
                    trace.record("plugin.execution", None, action_id=action.action_id, plugin=action.plugin, action=action.action.upper(), status=execution["status"])
                if execution["status"] == "SUCCESS":
                    successful_ids.add(action.action_id)
            if not progress:
                for action in deferred:
                    results.append({"action_id": action.action_id, "plugin": action.plugin, "action": action.action, "status": "ERROR", "result": {}, "message": "Dependencies could not be resolved."})
                break
            pending = deferred
        return results
