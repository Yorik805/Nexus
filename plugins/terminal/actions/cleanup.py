"""Cleanup action for the Nexus Terminal Plugin."""

from __future__ import annotations

from ..process_manager import PROCESS_MANAGER


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def cleanup(data: dict) -> dict:
    if data is not None and not isinstance(data, dict):
        return _build_response("ERROR", "CLEANUP requires a dictionary payload.")

    older_than_seconds = None
    if data is not None and "older_than_seconds" in data:
        value = data.get("older_than_seconds")
        if not isinstance(value, (int, float)):
            return _build_response("ERROR", "older_than_seconds must be a number.")
        older_than_seconds = float(value)

    removed = PROCESS_MANAGER.cleanup(older_than_seconds=older_than_seconds)
    return _build_response(
        "SUCCESS",
        "Cleanup completed.",
        {
            "removed_count": len(removed),
            "removed_process_ids": removed,
        },
    )
