"""Nexus Devices Plugin entry point.

This module routes incoming device plugin requests to the correct action handler.
"""

from __future__ import annotations

from .actions import list as list_module
from .actions import get as get_module
from .actions import send as send_module
from .actions import register as register_module
from .actions import disconnect as disconnect_module
from .actions import pending as pending_module

_SUPPORTED_ACTIONS = {
    "LIST": list_module.list_devices,
    "GET": get_module.get_device,
    "SEND": send_module.send_message,
    "REGISTER": register_module.register_device,
    "DISCONNECT": disconnect_module.disconnect_device,
    "PENDING": pending_module.list_pending,
}

_ACTION_CONTRACTS = {
    "LIST": {"description": "List all connected devices.", "required": {}, "optional": {}},
    "GET": {"description": "Get device details.", "required": {"device_id": {"type": "string"}}, "optional": {}},
    "SEND": {"description": "Send a message to a device.", "required": {"device_id": {"type": "string"}, "message": {"type": "string"}}, "optional": {}},
    "REGISTER": {"description": "Register a new device.", "required": {"device_id": {"type": "string"}, "device_type": {"type": "string"}}, "optional": {}},
    "DISCONNECT": {"description": "Disconnect a device.", "required": {"device_id": {"type": "string"}}, "optional": {}},
    "PENDING": {"description": "List pending messages from devices.", "required": {}, "optional": {"device_id": {"type": "string"}}},
}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def execute(request: dict) -> dict:
    """Execute a device plugin action.

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
