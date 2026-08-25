from __future__ import annotations

from typing import Any

from orchestrators import ActionRequest
from .registry import PluginRegistry


class PluginRouter:
    """Executes approved plugin actions in declared sequential order."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        actions: list[ActionRequest] | None,
        successful_action_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        successful_ids = set(successful_action_ids or ())
        for action in actions or []:
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
            if execution["status"] == "SUCCESS":
                successful_ids.add(action.action_id)
        return results
