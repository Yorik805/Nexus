# File System Plugin - API Reference

## Overview

The Nexus File System Plugin provides safe, sandboxed access to the local file system through 12 core operations. All operations follow the standard Nexus response format.

## Standard Response Format

All responses follow this format:

```json
{
    "status": "SUCCESS" | "ERROR",
    "message": "Human-readable message",
    "data": { }
}
```

## Operations

### READ

Reads the complete contents of a file.

**Request:**
```json
{
    "action": "READ",
    "data": {
        "path": "/path/to/file",
        "encoding": "utf-8"  // Optional, default: "utf-8"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "File read successfully.",
    "data": {
        "content": "file contents here",
        "encoding": "utf-8"
    }
}
```

**Errors:**
- Path is not a file or does not exist
- Invalid path format
- Failed to read file

---

### WRITE

Creates or overwrites a file with the provided content.

**Request:**
```json
{
    "action": "WRITE",
    "data": {
        "path": "/path/to/file",
        "content": "file content",
        "encoding": "utf-8"  // Optional, default: "utf-8"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "File written successfully.",
    "data": {
        "path": "/path/to/file",
        "size": 12,
        "encoding": "utf-8"
    }
}
```

**Errors:**
- Invalid path
- content is required
- Failed to write file

---

### APPEND

Appends content to the end of an existing file.

**Request:**
```json
{
    "action": "APPEND",
    "data": {
        "path": "/path/to/file",
        "content": "additional content",
        "encoding": "utf-8"  // Optional, default: "utf-8"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Content appended successfully.",
    "data": {
        "path": "/path/to/file",
        "appended_size": 18,
        "encoding": "utf-8"
    }
}
```

**Errors:**
- Path is not a file or does not exist
- content is required
- Failed to append to file

---

### DELETE

Deletes a file or directory from the file system.

**Request:**
```json
{
    "action": "DELETE",
    "data": {
        "path": "/path/to/target",
        "recursive": false  // Optional, default: false. Required for non-empty directories
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Path deleted successfully.",
    "data": {
        "path": "/path/to/target"
    }
}
```

**Errors:**
- Path does not exist
- Directory is not empty (without recursive=true)
- Failed to delete

---

### COPY

Copies a file or directory to a new location.

**Request:**
```json
{
    "action": "COPY",
    "data": {
        "source": "/path/to/source",
        "destination": "/path/to/destination",
        "recursive": true  // Optional, default: true. Required for directories
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Path copied successfully.",
    "data": {
        "source": "/path/to/source",
        "destination": "/path/to/destination"
    }
}
```

**Errors:**
- Source path does not exist
- Destination path already exists
- Source is directory without recursive=true
- Failed to copy

---

### MOVE

Moves (or renames) a file or directory to a new location.

**Request:**
```json
{
    "action": "MOVE",
    "data": {
        "source": "/path/to/source",
        "destination": "/path/to/destination"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Path moved successfully.",
    "data": {
        "source": "/path/to/source",
        "destination": "/path/to/destination"
    }
}
```

**Errors:**
- Source path does not exist
- Destination path already exists
- Failed to move

---

### RENAME

Renames a file or directory in place.

**Request:**
```json
{
    "action": "RENAME",
    "data": {
        "path": "/path/to/target",
        "new_name": "newname.txt"  // Just the name, not a path
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Path renamed successfully.",
    "data": {
        "old_path": "/path/to/target",
        "new_path": "/path/to/newname.txt"
    }
}
```

**Errors:**
- Path does not exist
- new_name is invalid
- New name already exists in the directory

---

### MKDIR

Creates a directory and optionally its parent directories.

**Request:**
```json
{
    "action": "MKDIR",
    "data": {
        "path": "/path/to/directory",
        "parents": true  // Optional, default: true
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Directory created successfully.",
    "data": {
        "path": "/path/to/directory"
    }
}
```

**Errors:**
- Invalid path
- Path exists but is not a directory
- Failed to create directory

---

### LIST

Lists the contents of a directory with metadata.

**Request:**
```json
{
    "action": "LIST",
    "data": {
        "path": "/path/to/directory",
        "include_hidden": false  // Optional, default: false
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Listed 3 entries.",
    "data": {
        "path": "/path/to/directory",
        "entries": [
            {
                "name": "file.txt",
                "type": "file",
                "size": 1024,
                "modified_at": 1629811200.0
            },
            {
                "name": "subdirectory",
                "type": "directory",
                "size": 4096,
                "modified_at": 1629811200.0
            }
        ],
        "count": 2
    }
}
```

**Errors:**
- Path is not a directory or does not exist
- Failed to list directory

---

### SEARCH

Searches for files matching a pattern in a directory.

**Request:**
```json
{
    "action": "SEARCH",
    "data": {
        "path": "/path/to/directory",
        "pattern": "*.txt",  // Optional, default: "*". Glob pattern matching
        "recursive": false,  // Optional, default: false
        "type": "file"       // Optional, default: "any". Options: "file", "directory", "any"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Found 3 matching entries.",
    "data": {
        "path": "/path/to/directory",
        "pattern": "*.txt",
        "results": [
            {
                "path": "/path/to/directory/file1.txt",
                "name": "file1.txt",
                "type": "file",
                "size": 512,
                "created_at": 1629811200.0,
                "modified_at": 1629811200.0,
                "accessed_at": 1629811200.0,
                "permissions": "644",
                "is_symlink": false
            }
        ],
        "count": 1
    }
}
```

**Errors:**
- Path is not a directory or does not exist
- Invalid type parameter
- Failed to search directory

---

### METADATA

Retrieves detailed metadata about a file or directory.

**Request:**
```json
{
    "action": "METADATA",
    "data": {
        "path": "/path/to/target"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Metadata retrieved successfully.",
    "data": {
        "metadata": {
            "path": "/path/to/file.txt",
            "name": "file.txt",
            "type": "file",
            "size": 1024,
            "created_at": 1629811200.0,
            "modified_at": 1629811200.0,
            "accessed_at": 1629811200.0,
            "permissions": "644",
            "is_symlink": false
        }
    }
}
```

**Errors:**
- Path does not exist
- Failed to retrieve metadata

---

### EXISTS

Checks if a path exists and determines its type.

**Request:**
```json
{
    "action": "EXISTS",
    "data": {
        "path": "/path/to/target"
    }
}
```

**Response (Success):**
```json
{
    "status": "SUCCESS",
    "message": "Path exists.",
    "data": {
        "path": "/path/to/target",
        "exists": true,
        "type": "file"  // "file", "directory", or null
    }
}
```

**Response (Not Found):**
```json
{
    "status": "SUCCESS",
    "message": "Path does not exist.",
    "data": {
        "path": "/path/to/target",
        "exists": false,
        "type": null
    }
}
```

**Errors:**
- Invalid path format

---

## Error Handling

All operations return `"status": "ERROR"` when something goes wrong. The `message` field provides a human-readable explanation.

Example error response:
```json
{
    "status": "ERROR",
    "message": "Path is not a file or does not exist.",
    "data": {}
}
```

## Path Handling

- Paths are automatically normalized and expanded (e.g., `~` is expanded to home directory)
- All paths are converted to absolute paths
- Relative paths are supported and are relative to the current working directory

## Security Considerations

- All paths are validated before operations
- Symlinks are followed but safe operations are used
- Permission errors are handled gracefully
- No direct system command execution is performed
