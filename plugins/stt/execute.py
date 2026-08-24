from __future__ import annotations

from .actions.detect_hardware import detect_hardware as detect_hardware_action
from .actions.get_device import get_device_action
from .actions.get_model import get_model_action
from .actions.load_model import load_model_action
from .actions.transcribe import transcribe_action
from .actions.unload_model import unload_model_action

_SUPPORTED_ACTIONS = {
    "DETECT_HARDWARE": detect_hardware_action,
    "LOAD_MODEL": load_model_action,
    "TRANSCRIBE": transcribe_action,
    "GET_MODEL": get_model_action,
    "GET_DEVICE": get_device_action,
    "UNLOAD_MODEL": unload_model_action,
}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def execute(request: dict) -> dict:
    """Execute an STT plugin action.

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
