"""Metadata operation for the Nexus File System Plugin.

Retrieves metadata about files and directories.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    get_file_metadata,
    path_exists,
    validate_path,
)


def metadata(data: dict) -> dict:
    """Get metadata about a file or directory.

    Request format:
    {
        "path": str
    }

    Returns:
        Standard response with file/directory metadata
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "METADATA requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check if path exists
    if not path_exists(path):
        return build_response("ERROR", "Path does not exist.")

    # Get metadata
    file_metadata = get_file_metadata(path)
    if file_metadata is None:
        return build_response("ERROR", "Failed to retrieve metadata.")

    return build_response(
        "SUCCESS",
        "Metadata retrieved successfully.",
        {"metadata": file_metadata},
    )
