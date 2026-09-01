"""Nexus Terminal Plugin entry point.

This module routes incoming terminal plugin requests to the correct action handler.
"""

from __future__ import annotations

from .actions import cleanup as cleanup_module
from .actions import execute as execute_module
from .actions import list as list_module
from .actions import status as status_module
from .actions import stop as stop_module
from .actions import update as update_module

_SUPPORTED_ACTIONS = {
    "EXECUTE": execute_module.execute_command,
    "STATUS": status_module.status,
    "STOP": stop_module.stop,
    "LIST": list_module.list_processes,
    "UPDATE": update_module.update,
    "CLEANUP": cleanup_module.cleanup,
}

_ACTION_CONTRACTS = {
    "EXECUTE": {
        "description": "Execute a terminal command.",
        "required": {"command": {"type": "string"}},
        "optional": {
            "cwd": {"type": "string"},
            "timeout": {"type": "number"},
            "environment": {"type": "object"},
            "dynamic": {"type": "boolean"},
            "update_interval": {"type": "integer"},
            "conversation_updates": {"type": "boolean"},
            "metadata": {"type": "object"},
        },
    },
    "STATUS": {"description": "Get terminal process status.", "required": {"process_id": {"type": "string"}}},
    "STOP": {"description": "Stop a terminal process.", "required": {"process_id": {"type": "string"}}},
    "LIST": {"description": "List terminal processes."},
    "UPDATE": {"description": "Update a terminal process.", "required": {"process_id": {"type": "string"}}},
    "CLEANUP": {"description": "Clean up terminal processes.", "optional": {"older_than_seconds": {"type": "number"}}},
}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def execute(request: dict) -> dict:
    """Execute a terminal plugin action.

    Args:
        request: A dictionary with keys "action" and "data".

    Returns:
        A standard response dictionary.
    """
    if not isinstance(request, dict):
        return _build_response(
            "ERROR",
            "Request must be a dictionary with action and data fields.",
        )

    action = str(request.get("action", "")).strip().upper()
    data = request.get("data", {})

    if action not in _SUPPORTED_ACTIONS:
        return _build_response(
            "ERROR",
            f"Unsupported action: {action}. Supported actions are: {', '.join(sorted(_SUPPORTED_ACTIONS))}.",
        )

    handler = _SUPPORTED_ACTIONS[action]
    try:
        return handler(data)
    except Exception as exc:  # pragma: no cover
        return _build_response(
            "ERROR",
            f"Unexpected error while executing action {action}: {exc}",
        )
