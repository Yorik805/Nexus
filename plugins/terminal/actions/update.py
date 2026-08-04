"""Update action for the Nexus Terminal Plugin."""

from __future__ import annotations

from ..process_manager import PROCESS_MANAGER


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def update(data: dict) -> dict:
    if not isinstance(data, dict):
        return _build_response("ERROR", "UPDATE requires a dictionary payload.")

    process_id = data.get("process_id")
    if not isinstance(process_id, str) or not process_id.strip():
        return _build_response("ERROR", "process_id must be a non-empty string.")

    update_interval = data.get("update_interval")
    conversation_updates = data.get("conversation_updates")
    continue_flag = data.get("continue_flag")
    metadata = data.get("metadata")

    if update_interval is not None and not isinstance(update_interval, int):
        return _build_response("ERROR", "update_interval must be an integer.")

    if conversation_updates is not None and not isinstance(conversation_updates, bool):
        return _build_response("ERROR", "conversation_updates must be a boolean.")

    if continue_flag is not None and not isinstance(continue_flag, bool):
        return _build_response("ERROR", "continue_flag must be a boolean.")

    if metadata is not None and not isinstance(metadata, dict):
        return _build_response("ERROR", "metadata must be a dictionary.")

    if update_interval is not None and update_interval < 0:
        return _build_response("ERROR", "update_interval must be zero or a positive integer.")

    success = PROCESS_MANAGER.update_process(
        process_id=process_id,
        update_interval=update_interval,
        conversation_updates=conversation_updates,
        continue_flag=continue_flag,
        metadata=metadata,
    )

    if not success:
        return _build_response("ERROR", f"Process not found: {process_id}")

    process = PROCESS_MANAGER.get_process(process_id)
    return _build_response(
        "SUCCESS",
        "Process updated successfully.",
        {
            "process_id": process_id,
            "process": process.to_dict() if process is not None else {},
        },
    )
