# Nexus Terminal Plugin

The Nexus Terminal Plugin provides a standardized, process-based execution layer for Nexus.
It is responsible for launching commands, tracking long-running jobs, streaming output, and maintaining process metadata for future integration with the Nexus runtime.

## Features

- Execute commands in foreground and dynamic background mode
- Track every command as a process with UUID, status, stdout/stderr, and runtime
- Capture output continuously and attach it to process metadata
- Graceful stop support via `continue_flag`
- Timeout support for foreground and dynamic execution
- Reusable process manager for future Nexus plugins
- Sandbox abstraction for future isolation layers
- Standard Nexus plugin interface

## Supported Actions

- `EXECUTE` - Launch a command
- `STATUS` - Query a process by its ID
- `STOP` - Gracefully stop a running process
- `LIST` - List all managed processes
- `CLEANUP` - Remove finished processes from the manager
- `UPDATE` - Modify process runtime properties

## Plugin Contract

All requests must use the standard Nexus format:

```json
{
  "action": "EXECUTE|STATUS|STOP|LIST|CLEANUP",
  "data": { ... }
}
```

All responses return the standard plugin response:

```json
{
  "status": "SUCCESS" | "ERROR",
  "message": "...",
  "data": { ... }
}
```

## Usage

```python
from plugins.terminal import execute

request = {
    "action": "EXECUTE",
    "data": {
        "command": "echo hello",
        "cwd": "/tmp",
        "dynamic": False,
    }
}

response = execute(request)
print(response)
```

## Process Lifecycle

1. `EXECUTE` creates a process
2. Process metadata is tracked in the process manager
3. `STATUS` returns current state and output
4. `STOP` terminates running processes gracefully
5. `CLEANUP` removes terminal records for finished processes
6. `UPDATE` changes process properties while running

## Sandbox Architecture

Current implementation uses subprocess through a `SandboxExecutor` abstraction.
Future sandbox implementations can replace the subprocess adapter without changing the public plugin API.

## Plugin Standard

This plugin follows the Nexus Plugin Standard used by the Memory and File System plugins.
It exposes a single public `execute(request: dict) -> dict` entry point and never raises exceptions outside the plugin.
