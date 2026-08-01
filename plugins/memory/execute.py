"""Nexus Memory Plugin entry point.

This module routes incoming requests to the correct operation module.
"""

from __future__ import annotations

from . import delete as delete_module
from . import get as get_module
from . import list as list_module
from . import search as search_module
from . import update as update_module
from . import write as write_module


_SUPPORTED_ACTIONS = {
    "WRITE": write_module.write,
    "SEARCH": search_module.search,
    "UPDATE": update_module.update,
    "DELETE": delete_module.delete,
    "GET": get_module.get,
    "LIST": list_module.list_memories,
}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def execute(request: dict) -> dict:
    """Execute a memory plugin action.

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
            f"Unsupported action: {action}. Supported actions are: {', '.join(_SUPPORTED_ACTIONS)}.",
        )

    handler = _SUPPORTED_ACTIONS[action]
    return handler(data)
