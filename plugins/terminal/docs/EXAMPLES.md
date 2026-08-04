# Nexus Terminal Plugin Examples

## Foreground Execution

```python
from plugins.terminal import execute

request = {
    "action": "EXECUTE",
    "data": {
        "command": "python -c \"print('hello')\"",
        "cwd": "/tmp",
        "dynamic": False,
    }
}
response = execute(request)
print(response)
```

## Dynamic Execution

```python
from plugins.terminal import execute

request = {
    "action": "EXECUTE",
    "data": {
        "command": "python -c \"import time; print('start'); time.sleep(5); print('done')\"",
        "dynamic": True,
        "update_interval": 1000,
        "conversation_updates": True,
    }
}
response = execute(request)
print(response)
```

## Querying Status

```python
from plugins.terminal import execute

request = {
    "action": "STATUS",
    "data": {
        "process_id": "<process_id>"
    }
}
response = execute(request)
print(response)
```

## Updating a Process

```python
from plugins.terminal import execute

request = {
    "action": "UPDATE",
    "data": {
        "process_id": "<process_id>",
        "update_interval": 500,
        "conversation_updates": False,
    }
}
response = execute(request)
print(response)
```

## Stopping a Process

```python
from plugins.terminal import execute

request = {
    "action": "STOP",
    "data": {
        "process_id": "<process_id>"
    }
}
response = execute(request)
print(response)
```

## Cleaning Up Finished Processes

```python
from plugins.terminal import execute

request = {
    "action": "CLEANUP",
    "data": {
        "older_than_seconds": 3600
    }
}
response = execute(request)
print(response)
```
