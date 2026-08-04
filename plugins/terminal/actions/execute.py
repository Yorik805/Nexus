"""Execute action for the Nexus Terminal Plugin."""

from __future__ import annotations

from ..process_manager import PROCESS_MANAGER


def _build_response(status: str, message: str, data: dict | None = None) -> dict:
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def _normalize_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError("Value must be a boolean.")


def _normalize_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    raise ValueError("Value must be an integer.")


def execute_command(data: dict) -> dict:
    if not isinstance(data, dict):
        return _build_response("ERROR", "EXECUTE requires a dictionary payload.")

    command = data.get("command")
    cwd = data.get("cwd")
    environment = data.get("environment")
    timeout = data.get("timeout")
    dynamic = data.get("dynamic", False)
    update_interval = data.get("update_interval", 1000)
    conversation_updates = data.get("conversation_updates", False)
    metadata = data.get("metadata", {})

    if command is None:
        return _build_response("ERROR", "command is required.")

    if not isinstance(command, (str, list)):
        return _build_response("ERROR", "command must be a string or list of strings.")

    if cwd is not None and not isinstance(cwd, str):
        return _build_response("ERROR", "cwd must be a string.")

    if environment is not None and not isinstance(environment, dict):
        return _build_response("ERROR", "environment must be a dictionary.")

    if timeout is not None and not isinstance(timeout, (int, float)):
        return _build_response("ERROR", "timeout must be a number.")

    try:
        dynamic_value = _normalize_bool(dynamic, False)
        update_interval_value = _normalize_int(update_interval, 1000)
        conversation_updates_value = _normalize_bool(conversation_updates, False)
    except ValueError as exc:
        return _build_response("ERROR", str(exc))

    if update_interval_value < 0:
        return _build_response("ERROR", "update_interval must be zero or a positive integer.")

    if timeout is not None and timeout <= 0:
        timeout_value = None
    else:
        timeout_value = float(timeout) if timeout is not None else None

    try:
        process = PROCESS_MANAGER.create_process(
            command=command,
            cwd=cwd,
            environment=environment,
            timeout=timeout_value,
            dynamic=dynamic_value,
            update_interval=update_interval_value,
            conversation_updates=conversation_updates_value,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
    except Exception as exc:  # pragma: no cover
        return _build_response("ERROR", f"Failed to create process: {exc}")

    if dynamic_value:
        if process.status != "RUNNING":
            return _build_response(
                "ERROR",
                process.message or "Process failed to start in dynamic mode.",
                {
                    "process_id": process.process_id,
                    "status": process.status,
                    "started_at": process.started_at,
                },
            )

        return _build_response(
            "SUCCESS",
            "Process started in dynamic mode.",
            {
                "process_id": process.process_id,
                "status": process.status,
                "started_at": process.started_at,
            },
        )

    process.wait_for_completion()

    if process.status == "FAILED":
        return _build_response(
            "ERROR",
            process.message or "Process execution failed.",
            {
                "process_id": process.process_id,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.exit_code,
                "runtime": process.runtime,
            },
        )

    if process.status == "TIMED_OUT":
        return _build_response(
            "ERROR",
            process.message or "Process timed out.",
            {
                "process_id": process.process_id,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.exit_code,
                "runtime": process.runtime,
            },
        )

    return _build_response(
        "SUCCESS",
        "Process completed.",
        {
            "process_id": process.process_id,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "exit_code": process.exit_code,
            "runtime": process.runtime,
        },
    )
