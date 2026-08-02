"""Exists operation for the Nexus File System Plugin.

Checks if a path exists and what type it is.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    is_dir,
    is_file,
    path_exists,
    validate_path,
)


def exists(data: dict) -> dict:
    """Check if a path exists and determine its type.

    Request format:
    {
        "path": str
    }

    Returns:
        Standard response with existence status and type
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "EXISTS requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check existence
    exists_flag = path_exists(path)

    if not exists_flag:
        return build_response(
            "SUCCESS",
            "Path does not exist.",
            {
                "path": str(path),
                "exists": False,
                "type": None,
            },
        )

    # Determine type
    path_type = None
    if is_file(path):
        path_type = "file"
    elif is_dir(path):
        path_type = "directory"

    return build_response(
        "SUCCESS",
        "Path exists.",
        {
            "path": str(path),
            "exists": True,
            "type": path_type,
        },
    )
