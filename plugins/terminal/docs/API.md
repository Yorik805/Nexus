# Nexus Terminal Plugin API

## Overview

The Terminal Plugin exposes a standard Nexus plugin API with the following actions:

- `EXECUTE`
- `STATUS`
- `STOP`
- `LIST`
- `UPDATE`
- `CLEANUP`

Every request must include an `action` string and a `data` dictionary.
Every response uses the standard Nexus response shape.

---

## EXECUTE

### Request

```json
{
  "action": "EXECUTE",
  "data": {
    "command": "...",
    "cwd": "...",
    "environment": {},
    "timeout": 60,
    "dynamic": true,
    "update_interval": 1000,
    "conversation_updates": true,
    "metadata": {}
  }
}
```

### Response (dynamic)

```json
{
  "status": "SUCCESS",
  "message": "Process started in dynamic mode.",
  "data": {
    "process_id": "...",
    "status": "RUNNING",
    "started_at": "..."
  }
}
```

### Response (foreground)

```json
{
  "status": "SUCCESS",
  "message": "Process completed.",
  "data": {
    "process_id": "...",
    "stdout": "...",
    "stderr": "...",
    "exit_code": 0,
    "runtime": 0.12
  }
}
```

---

## STATUS

### Request

```json
{
  "action": "STATUS",
  "data": {
    "process_id": "..."
  }
}
```

### Response

```json
{
  "status": "SUCCESS",
  "message": "Process status retrieved.",
  "data": {
    "process_id": "...",
    "command": "...",
    "cwd": "...",
    "environment": {},
    "status": "RUNNING",
    "pid": 1234,
    "started_at": "...",
    "finished_at": null,
    "stdout": "...",
    "stderr": "...",
    "exit_code": null,
    "runtime": null,
    "dynamic": true,
    "update_interval": 1000,
    "continue_flag": true,
    "conversation_updates": false,
    "metadata": {},
    "message": ""
  }
}
```

---

## STOP

### Request

```json
{
  "action": "STOP",
  "data": {
    "process_id": "..."
  }
}
```

### Response

```json
{
  "status": "Failed",
  "message": "Process stop requested.",
  "data": {
    "process_id": "...",
    "status": "STOPPED",
    "finished_at": "..."
  }
}
```

---

## LIST

### Request

```json
{
  "action": "LIST",
  "data": {}
}
```

### Response

```json
{
  "status": "SUCCESS",
  "message": "Process list retrieved.",
  "data": {
    "processes": [ ... ]
  }
}
```

---

## UPDATE

### Request

```json
{
  "action": "UPDATE",
  "data": {
    "process_id": "...",
    "update_interval": 500,
    "conversation_updates": true,
    "continue_flag": true,
    "metadata": {}
  }
}
```

### Response

```json
{
  "status": "SUCCESS",
  "message": "Process updated successfully.",
  "data": {
    "process_id": "...",
    "process": { ... }
  }
}
```

## CLEANUP

### Request

```json
{
  "action": "CLEANUP",
  "data": {
    "older_than_seconds": 3600
  }
}
```

### Response

```json
{
  "status": "SUCCESS",
  "message": "Cleanup completed.",
  "data": {
    "removed_count": 1,
    "removed_process_ids": ["..."]
  }
}
```
