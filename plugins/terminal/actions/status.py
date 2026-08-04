"""Status action for the Nexus Terminal Plugin."""

from __future__ import annotations

from ..process_manager import PROCESS_MANAGER


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def status(data: dict) -> dict:
    if not isinstance(data, dict):
        return _build_response("ERROR", "STATUS requires a dictionary payload.")

    process_id = data.get("process_id")
    if not isinstance(process_id, str) or not process_id.strip():
        return _build_response("ERROR", "process_id must be a non-empty string.")

    process = PROCESS_MANAGER.get_process(process_id)
    if process is None:
        return _build_response("ERROR", f"Process not found: {process_id}")

    return _build_response(
        "SUCCESS",
        "Process status retrieved.",
        process.to_dict(),
    )
