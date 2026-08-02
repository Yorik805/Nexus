"""Make directory operation for the Nexus File System Plugin.

Creates directories in the file system.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    safe_mkdir,
    validate_path,
)


def mkdir(data: dict) -> dict:
    """Create a directory (and parents if needed).

    Request format:
    {
        "path": str,
        "parents": bool (optional, default true)
    }

    Returns:
        Standard response with created directory path
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "MKDIR requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Get parents flag
    parents = bool(data.get("parents", True))

    # Create directory
    success, error_msg = safe_mkdir(path, parents=parents)
    if not success:
        return build_response("ERROR", error_msg)

    return build_response(
        "SUCCESS",
        "Directory created successfully.",
        {"path": str(path)},
    )
