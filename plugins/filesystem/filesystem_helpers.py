"""File System Plugin common utilities and helpers.

This module provides shared functions for path validation, error handling,
and response formatting.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def build_response(status: str, message: str, data: dict | None = None) -> dict:
    """Build a standard Nexus response dictionary.

    Args:
        status: "SUCCESS" or "ERROR"
        message: Human-readable message
        data: Optional data payload

    Returns:
        Standard response dict
    """
    return {
        "status": status,
        "message": message,
        "data": data or {},
    }


def validate_path(path_str: str) -> tuple[bool, str, Path | None]:
    """Validate and normalize a file path.

    Args:
        path_str: Path string to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_path)
    """
    if not isinstance(path_str, str) or not path_str.strip():
        return False, "Path must be a non-empty string.", None

    try:
        path = Path(path_str.strip()).expanduser().resolve()
        return True, "", path
    except (ValueError, RuntimeError, OSError):
        return False, "Invalid path format.", None


def path_exists(path: Path) -> bool:
    """Check if a path exists."""
    try:
        return path.exists()
    except (OSError, ValueError):
        return False


def is_file(path: Path) -> bool:
    """Check if path is a file."""
    try:
        return path.is_file()
    except (OSError, ValueError):
        return False


def is_dir(path: Path) -> bool:
    """Check if path is a directory."""
    try:
        return path.is_dir()
    except (OSError, ValueError):
        return False


def get_file_metadata(path: Path) -> dict[str, Any] | None:
    """Get metadata for a file or directory.

    Args:
        path: Path object

    Returns:
        Dict with metadata or None if path doesn't exist
    """
    if not path_exists(path):
        return None

    try:
        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "type": "directory" if is_dir(path) else "file",
            "size": stat.st_size,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
            "accessed_at": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:],
            "is_symlink": path.is_symlink(),
        }
    except (OSError, ValueError):
        return None


def get_directory_contents(path: Path, include_hidden: bool = False) -> list[dict[str, Any]] | None:
    """Get contents of a directory.

    Args:
        path: Path to directory
        include_hidden: Whether to include hidden files

    Returns:
        List of entry dicts or None if not a directory or error
    """
    if not is_dir(path):
        return None

    try:
        entries: list[dict[str, Any]] = []
        for entry in sorted(path.iterdir()):
            if not include_hidden and entry.name.startswith("."):
                continue

            try:
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size,
                    "modified_at": stat.st_mtime,
                })
            except (OSError, ValueError):
                # Skip inaccessible entries
                continue

        return entries
    except (OSError, ValueError):
        return None


def normalize_encoding(value: str | None, default: str = "utf-8") -> str:
    """Normalize encoding parameter.

    Args:
        value: Encoding string
        default: Default encoding

    Returns:
        Valid encoding string
    """
    if not value:
        return default
    encoding = str(value).strip().lower()
    return encoding if encoding else default


def safe_read_file(path: Path, encoding: str = "utf-8") -> tuple[bool, str | bytes]:
    """Safely read file contents.

    Args:
        path: Path to file
        encoding: Text encoding to use

    Returns:
        Tuple of (success, contents or error_message)
    """
    if not is_file(path):
        return False, "Path is not a file."

    try:
        with open(path, "r", encoding=encoding) as f:
            return True, f.read()
    except UnicodeDecodeError:
        # Try binary read if text fails
        try:
            with open(path, "rb") as f:
                return True, f.read()
        except (OSError, IOError):
            return False, "Failed to read file (binary mode)."
    except (OSError, IOError):
        return False, "Failed to read file."


def safe_write_file(path: Path, content: str | bytes, encoding: str = "utf-8") -> tuple[bool, str]:
    """Safely write file contents.

    Args:
        path: Path to file
        content: Content to write
        encoding: Text encoding to use

    Returns:
        Tuple of (success, error_message if failed)
    """
    try:
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            with open(path, "wb") as f:
                f.write(content)
        else:
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
        return True, ""
    except (OSError, IOError, UnicodeEncodeError) as e:
        return False, f"Failed to write file: {str(e)}"


def safe_append_file(path: Path, content: str | bytes, encoding: str = "utf-8") -> tuple[bool, str]:
    """Safely append to file contents.

    Args:
        path: Path to file
        content: Content to append
        encoding: Text encoding to use

    Returns:
        Tuple of (success, error_message if failed)
    """
    if not is_file(path):
        return False, "Path is not a file."

    try:
        if isinstance(content, bytes):
            with open(path, "ab") as f:
                f.write(content)
        else:
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
        return True, ""
    except (OSError, IOError, UnicodeEncodeError) as e:
        return False, f"Failed to append to file: {str(e)}"


def safe_delete(path: Path, recursive: bool = False) -> tuple[bool, str]:
    """Safely delete a file or directory.

    Args:
        path: Path to delete
        recursive: Whether to recursively delete directories

    Returns:
        Tuple of (success, error_message if failed)
    """
    if not path_exists(path):
        return False, "Path does not exist."

    try:
        if is_file(path):
            path.unlink()
            return True, ""
        elif is_dir(path):
            if not recursive:
                # Check if directory is empty
                if any(path.iterdir()):
                    return False, "Directory is not empty. Use recursive=true to delete with contents."
                path.rmdir()
            else:
                # Recursive delete
                import shutil
                shutil.rmtree(path)
            return True, ""
        else:
            return False, "Path is neither a file nor a directory."
    except (OSError, IOError) as e:
        return False, f"Failed to delete: {str(e)}"


def safe_copy(source: Path, destination: Path, recursive: bool = True) -> tuple[bool, str]:
    """Safely copy a file or directory.

    Args:
        source: Source path
        destination: Destination path
        recursive: Whether to recursively copy directories

    Returns:
        Tuple of (success, error_message if failed)
    """
    if not path_exists(source):
        return False, "Source path does not exist."

    if path_exists(destination):
        return False, "Destination path already exists."

    try:
        import shutil
        if is_file(source):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        elif is_dir(source):
            if not recursive:
                return False, "Source is a directory. Use recursive=true to copy with contents."
            shutil.copytree(source, destination)
        else:
            return False, "Source is neither a file nor a directory."
        return True, ""
    except (OSError, IOError) as e:
        return False, f"Failed to copy: {str(e)}"


def safe_move(source: Path, destination: Path) -> tuple[bool, str]:
    """Safely move (rename) a file or directory.

    Args:
        source: Source path
        destination: Destination path

    Returns:
        Tuple of (success, error_message if failed)
    """
    if not path_exists(source):
        return False, "Source path does not exist."

    if path_exists(destination):
        return False, "Destination path already exists."

    try:
        import shutil
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return True, ""
    except (OSError, IOError) as e:
        return False, f"Failed to move: {str(e)}"


def safe_rename(path: Path, new_name: str) -> tuple[bool, str]:
    """Safely rename a file or directory.

    Args:
        path: Path to rename
        new_name: New name (not a full path)

    Returns:
        Tuple of (success, error_message if failed)
    """
    if not path_exists(path):
        return False, "Path does not exist."

    if not new_name or "/" in new_name or "\\" in new_name:
        return False, "Invalid new name."

    try:
        new_path = path.parent / new_name
        if path.exists() and new_path.exists():
            return False, "Destination name already exists."
        path.rename(new_path)
        return True, ""
    except (OSError, IOError) as e:
        return False, f"Failed to rename: {str(e)}"


def safe_mkdir(path: Path, parents: bool = True) -> tuple[bool, str]:
    """Safely create a directory.

    Args:
        path: Directory path to create
        parents: Whether to create parent directories

    Returns:
        Tuple of (success, error_message if failed)
    """
    if path_exists(path):
        if is_dir(path):
            return True, ""  # Directory already exists
        else:
            return False, "Path exists but is not a directory."

    try:
        path.mkdir(parents=parents, exist_ok=True)
        return True, ""
    except (OSError, IOError) as e:
        return False, f"Failed to create directory: {str(e)}"
