"""Nexus File System Plugin entry point.

This module routes incoming requests to the appropriate file system action.
"""

from __future__ import annotations

from .actions import append as append_module
from .actions import copy as copy_module
from .actions import delete as delete_module
from .actions import exists as exists_module
from .actions import list as list_module
from .actions import metadata as metadata_module
from .actions import mkdir as mkdir_module
from .actions import move as move_module
from .actions import read as read_module
from .actions import rename as rename_module
from .actions import search as search_module
from .actions import write as write_module


_SUPPORTED_ACTIONS = {
    "READ": read_module.read,
    "WRITE": write_module.write,
    "APPEND": append_module.append,
    "DELETE": delete_module.delete,
    "COPY": copy_module.copy,
    "MOVE": move_module.move,
    "RENAME": rename_module.rename,
    "MKDIR": mkdir_module.mkdir,
    "LIST": list_module.list,
    "SEARCH": search_module.search,
    "METADATA": metadata_module.metadata,
    "EXISTS": exists_module.exists,
}

_ACTION_CONTRACTS = {
    action: {"description": f"Filesystem {action.lower()} operation.", "required": {"path": {"type": "string"}}}
    for action in ("READ", "WRITE", "APPEND", "DELETE", "EXISTS", "METADATA", "LIST", "SEARCH")
}
_ACTION_CONTRACTS["WRITE"]["required"] = {"path": {"type": "string"}, "content": {"type": "string"}}
_ACTION_CONTRACTS["APPEND"]["required"] = {"path": {"type": "string"}, "content": {"type": "string"}}
_ACTION_CONTRACTS["COPY"] = {"required": {"source": {"type": "string"}, "destination": {"type": "string"}}}
_ACTION_CONTRACTS["MOVE"] = _ACTION_CONTRACTS["COPY"]
_ACTION_CONTRACTS["RENAME"] = {"required": {"path": {"type": "string"}, "new_name": {"type": "string"}}}
_ACTION_CONTRACTS["MKDIR"] = {"required": {"path": {"type": "string"}}}


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def execute(request: dict) -> dict:
    """Execute a file system plugin action.

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
    return handler(data)
