"""Append file operation for the Nexus File System Plugin.

Appends content to the end of an existing file.
"""

from __future__ import annotations

from pathlib import Path

from ..filesystem_helpers import (
    build_response,
    is_file,
    normalize_encoding,
    safe_append_file,
    validate_path,
)


def append(data: dict) -> dict:
    """Append content to the end of a file.

    Request format:
    {
        "path": str,
        "content": str | bytes,
        "encoding": str (optional, default "utf-8")
    }

    Returns:
        Standard response with path information
    """
    if not isinstance(data, dict):
        return build_response("ERROR", "APPEND requires a dictionary payload.")

    # Validate path
    is_valid, error_msg, path = validate_path(data.get("path"))
    if not is_valid:
        return build_response("ERROR", error_msg)

    # Check if file exists
    if not is_file(path):
        return build_response("ERROR", "Path is not a file or does not exist.")

    # Get content
    content = data.get("content")
    if content is None:
        return build_response("ERROR", "content is required.")
    if not isinstance(content, (str, bytes)):
        return build_response("ERROR", "content must be a string or bytes.")

    # Get encoding
    encoding = normalize_encoding(data.get("encoding"))

    # Append to file
    success, error_msg = safe_append_file(path, content, encoding)
    if not success:
        return build_response("ERROR", error_msg)

    return build_response(
        "SUCCESS",
        "Content appended successfully.",
        {
            "path": str(path),
            "appended_size": len(content),
            "encoding": encoding if isinstance(content, str) else "bytes",
        },
    )
