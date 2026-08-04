"""List action for the Nexus Terminal Plugin."""

from __future__ import annotations

from ..process_manager import PROCESS_MANAGER


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def list_processes(data: dict) -> dict:
    if data is not None and not isinstance(data, dict):
        return _build_response("ERROR", "LIST requires a dictionary payload.")

    return _build_response(
        "SUCCESS",
        "Process list retrieved.",
        {"processes": PROCESS_MANAGER.list_processes()},
    )
