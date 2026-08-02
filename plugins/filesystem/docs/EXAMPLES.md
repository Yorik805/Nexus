# File System Plugin - Examples

This document provides practical examples of using the File System Plugin.

## Basic File Operations

### Writing a File

```python
request = {
    "action": "WRITE",
    "data": {
        "path": "/tmp/hello.txt",
        "content": "Hello, World!"
    }
}
# Response: SUCCESS, file created with content
```

### Reading a File

```python
request = {
    "action": "READ",
    "data": {
        "path": "/tmp/hello.txt"
    }
}
# Response: SUCCESS with data["content"] = "Hello, World!"
```

### Appending to a File

```python
request = {
    "action": "APPEND",
    "data": {
        "path": "/tmp/hello.txt",
        "content": "\nGoodbye, World!"
    }
}
# Response: SUCCESS, content appended
```

## Directory Operations

### Creating a Directory

```python
request = {
    "action": "MKDIR",
    "data": {
        "path": "/tmp/my_project/src/data"
        # parents=true by default, so all parent directories are created
    }
}
# Response: SUCCESS, all directories created
```

### Listing Directory Contents

```python
request = {
    "action": "LIST",
    "data": {
        "path": "/tmp/my_project"
    }
}
# Response: SUCCESS with entries array containing file/directory metadata
```

## File Management

### Copying a File

```python
request = {
    "action": "COPY",
    "data": {
        "source": "/tmp/hello.txt",
        "destination": "/tmp/hello_backup.txt"
    }
}
# Response: SUCCESS, file copied
```

### Moving/Renaming a File

```python
request = {
    "action": "MOVE",
    "data": {
        "source": "/tmp/hello.txt",
        "destination": "/tmp/greetings.txt"
    }
}
# Response: SUCCESS, file moved
```

### Using RENAME (in-place)

```python
request = {
    "action": "RENAME",
    "data": {
        "path": "/tmp/greetings.txt",
        "new_name": "salutations.txt"
    }
}
# Response: SUCCESS with old_path and new_path
```

### Deleting a File

```python
request = {
    "action": "DELETE",
    "data": {
        "path": "/tmp/salutations.txt"
    }
}
# Response: SUCCESS, file deleted
```

### Deleting a Directory

```python
request = {
    "action": "DELETE",
    "data": {
        "path": "/tmp/my_project",
        "recursive": true  # Required for non-empty directories
    }
}
# Response: SUCCESS, directory and all contents deleted
```

## Searching and Discovery

### Searching for Files by Pattern

```python
request = {
    "action": "SEARCH",
    "data": {
        "path": "/tmp",
        "pattern": "*.txt",
        "recursive": true
    }
}
# Response: SUCCESS with results array of matching files
```

### Searching for Directories Only

```python
request = {
    "action": "SEARCH",
    "data": {
        "path": "/tmp",
        "type": "directory",
        "recursive": true
    }
}
# Response: SUCCESS with results array of matching directories
```

### Getting File Metadata

```python
request = {
    "action": "METADATA",
    "data": {
        "path": "/tmp/hello.txt"
    }
}
# Response: SUCCESS with metadata including size, permissions, timestamps
```

### Checking If Path Exists

```python
request = {
    "action": "EXISTS",
    "data": {
        "path": "/tmp/hello.txt"
    }
}
# Response: SUCCESS with exists=true/false and type="file"/"directory"/null
```

## Advanced Scenarios

### Copy Directory Recursively

```python
request = {
    "action": "COPY",
    "data": {
        "source": "/tmp/my_project",
        "destination": "/tmp/my_project_backup",
        "recursive": true
    }
}
# Response: SUCCESS, entire directory tree copied
```

### Search with Multiple Criteria

```python
# Find all text files in project
request = {
    "action": "SEARCH",
    "data": {
        "path": "/tmp/my_project",
        "pattern": "*.txt",
        "type": "file",
        "recursive": true
    }
}
```

### Working with Hidden Files

```python
request = {
    "action": "LIST",
    "data": {
        "path": "/tmp",
        "include_hidden": true  # Include .gitignore, .env, etc.
    }
}
# Response: SUCCESS with hidden files included
```

## Error Scenarios

### Attempting to Read Non-existent File

```python
request = {
    "action": "READ",
    "data": {"path": "/tmp/nonexistent.txt"}
}
# Response: ERROR "Path is not a file or does not exist."
```

### Attempting to Append to Non-existent File

```python
request = {
    "action": "APPEND",
    "data": {
        "path": "/tmp/nonexistent.txt",
        "content": "text"
    }
}
# Response: ERROR "Path is not a file or does not exist."
```

### Attempting to Delete Non-empty Directory Without Recursive

```python
request = {
    "action": "DELETE",
    "data": {
        "path": "/tmp/my_project"
        # recursive not set (defaults to false)
    }
}
# Response: ERROR "Directory is not empty. Use recursive=true..."
```

### Path Already Exists

```python
request = {
    "action": "COPY",
    "data": {
        "source": "/tmp/file1.txt",
        "destination": "/tmp/file2.txt"  # file2.txt already exists
    }
}
# Response: ERROR "Destination path already exists."
```

## Home Directory Expansion

All of these work with `~` for home directory:

```python
# Write to home directory
request = {
    "action": "WRITE",
    "data": {
        "path": "~/documents/note.txt",
        "content": "My note"
    }
}
# Path is expanded to /home/username/documents/note.txt
```

## Response Examples

### Successful LIST Response

```json
{
    "status": "SUCCESS",
    "message": "Listed 3 entries.",
    "data": {
        "path": "/tmp",
        "entries": [
            {
                "name": "hello.txt",
                "type": "file",
                "size": 13,
                "modified_at": 1691234567.0
            },
            {
                "name": "my_project",
                "type": "directory",
                "size": 4096,
                "modified_at": 1691234567.0
            }
        ],
        "count": 2
    }
}
```

### Successful SEARCH Response

```json
{
    "status": "SUCCESS",
    "message": "Found 2 matching entries.",
    "data": {
        "path": "/tmp",
        "pattern": "*.txt",
        "results": [
            {
                "path": "/tmp/hello.txt",
                "name": "hello.txt",
                "type": "file",
                "size": 13,
                "created_at": 1691234567.0,
                "modified_at": 1691234567.0,
                "accessed_at": 1691234567.0,
                "permissions": "644",
                "is_symlink": false
            }
        ],
        "count": 1
    }
}
```

### Error Response

```json
{
    "status": "ERROR",
    "message": "Path is not a file or does not exist.",
    "data": {}
}
```
