# File System Plugin

The File System Plugin provides safe, sandboxed access to the local file system.

It allows Nexus to read, write, and manipulate files and directories with proper validation and error handling.

## Features

**File Operations:**
- READ - Read file contents
- WRITE - Create or overwrite files
- APPEND - Append to files
- DELETE - Delete files and directories

**File Management:**
- COPY - Copy files and directories
- MOVE - Move or rename files and directories
- RENAME - In-place renaming

**Directory Operations:**
- MKDIR - Create directories
- LIST - List directory contents
- EXISTS - Check if path exists

**Discovery:**
- SEARCH - Find files matching patterns
- METADATA - Get file/directory metadata

## Architecture

Following the Nexus Plugin Standard, the File System Plugin:

- Exposes a single `execute(request: dict) -> dict` function
- Routes all actions through the dispatcher
- Returns standardized responses
- Validates all inputs
- Handles errors gracefully
- Uses only Python standard library

## Request Format

All requests follow this format:

```json
{
    "action": "READ|WRITE|APPEND|DELETE|COPY|MOVE|RENAME|MKDIR|LIST|SEARCH|METADATA|EXISTS",
    "data": {
        // Action-specific parameters
    }
}
```

## Response Format

All responses follow this format:

```json
{
    "status": "SUCCESS" | "ERROR",
    "message": "Human-readable message",
    "data": {
        // Action-specific response data
    }
}
```

## Usage Example

```python
from plugins.filesystem import execute

# Read a file
request = {
    "action": "READ",
    "data": {
        "path": "/path/to/file.txt"
    }
}
response = execute(request)

if response["status"] == "SUCCESS":
    print("File contents:", response["data"]["content"])
else:
    print("Error:", response["message"])
```

## Path Handling

- Paths are automatically normalized and expanded
- `~` is expanded to the user's home directory
- Relative paths are supported
- All paths are converted to absolute paths

## Error Handling

All operations:
- Never crash or raise exceptions
- Always return a standard response
- Provide clear error messages
- Handle permission errors gracefully

## Security

The File System Plugin implements:

- Path validation and normalization
- Safe filesystem operations
- No shell command execution
- Proper error handling
- Permission-aware operations

## API Documentation

See [docs/API.md](docs/API.md) for complete API reference with all operation details.

See [docs/EXAMPLES.md](docs/EXAMPLES.md) for practical usage examples.

## Plugin Standard

This plugin complies with the [Nexus Plugin Standard](/docs/PLUGIN_STANDARD.md).

## Supported Actions

| Action | Purpose |
|--------|---------|
| READ | Read file contents |
| WRITE | Create or overwrite file |
| APPEND | Append to file |
| DELETE | Delete file or directory |
| COPY | Copy file or directory |
| MOVE | Move file or directory |
| RENAME | Rename file or directory |
| MKDIR | Create directory |
| LIST | List directory contents |
| SEARCH | Search for files by pattern |
| METADATA | Get file/directory metadata |
| EXISTS | Check if path exists |
