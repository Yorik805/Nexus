# Memory Plugin API Examples

This document contains practical request and response examples for the supported Memory Plugin operations. It is intended as an official reference for developers working with the Nexus Memory Plugin.

---

## Standard Request Format

All Memory Plugin API requests share a common structure. Every request is a JSON object containing an `action` field and a `data` payload.

```json
{
    "action": "...",
    "data": {}
}
```

- `action` is the operation name, such as `WRITE`, `SEARCH`, or `GET`.
- `data` contains the payload specific to the requested operation.

---

## Standard Response Format

The Memory Plugin returns a standardized response object for all operations.

```json
{
    "status": "SUCCESS" | "ERROR",
    "message": "...",
    "data": {}
}
```

- `status` indicates whether the request succeeded or failed.
- `message` provides a human-readable summary of the result.
- `data` contains operation-specific response values.

---

## WRITE Examples

### Valid Request

```json
{
    "action": "WRITE",
    "data": {
        "title": "Launch Planning Notes",
        "category": "PROJECT",
        "content": "Prepare the launch checklist and review team readiness.",
        "tags": ["launch", "planning", "project"]
    }
}
```

### Successful Response

```json
{
    "status": "SUCCESS",
    "message": "Memory stored successfully.",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2026-08-01T12:00:00+00:00",
        "version": 1
    }
}
```

### Invalid Request Example

```json
{
    "action": "WRITE",
    "data": {
        "title": "",
        "category": "project",
        "content": "",
        "tags": ["", 123]
    }
}
```

### Validation Error Response

```json
{
    "status": "ERROR",
    "message": "title must be a non-empty string.",
    "data": {}
}
```

> Note: `category` must be one of the supported constants: `PROJECT`, `PERSON`, `IDEA`, or `PREFERENCE`.

---

## SEARCH Examples

### Simple Search

```json
{
    "action": "SEARCH",
    "data": {
        "query": "launch",
        "category": null,
        "tags": null,
        "limit": 10
    }
}
```

### Search with Category

```json
{
    "action": "SEARCH",
    "data": {
        "query": "planning",
        "category": "PROJECT",
        "tags": null,
        "limit": 5
    }
}
```

### Search with Tags

```json
{
    "action": "SEARCH",
    "data": {
        "query": "review",
        "category": null,
        "tags": ["planning", "project"],
        "limit": 5
    }
}
```

### Search Including Deleted Memories

```json
{
    "action": "SEARCH",
    "data": {
        "query": "review",
        "include_deleted": true,
        "limit": 10
    }
}
```

### Search Response with Results

```json
{
    "status": "SUCCESS",
    "message": "Found 2 matching memories.",
    "data": {
        "results": [
            {
                "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Launch Planning Notes",
                "category": "PROJECT",
                "created_at": "2026-08-01T12:00:00+00:00"
            },
            {
                "memory_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "Project Review Agenda",
                "category": "PROJECT",
                "created_at": "2026-08-01T12:30:00+00:00"
            }
        ]
    }
}
```

### Empty Results Response

```json
{
    "status": "SUCCESS",
    "message": "No matching memories found.",
    "data": {
        "results": []
    }
}
```

---

## GET Examples

### Valid Request

```json
{
    "action": "GET",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

### Successful Response

```json
{
    "status": "SUCCESS",
    "message": "Memory fetched successfully.",
    "data": {
        "memory": {
            "memory_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Launch Planning Notes",
            "category": "PROJECT",
            "content": "Prepare the launch checklist and review team readiness.",
            "tags": ["launch", "planning", "project"],
            "created_at": "2026-08-01T12:00:00+00:00",
            "updated_at": "2026-08-01T12:00:00+00:00",
            "version": 1,
            "deleted": false,
            "deleted_at": null
        }
    }
}
```

### Deleted Memory Request

```json
{
    "action": "GET",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000",
        "include_deleted": true
    }
}
```

---

## UPDATE Examples

### Valid Request

```json
{
    "action": "UPDATE",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000",
        "changes": {
            "title": "Launch Planning Notes (Updated)",
            "content": "Update the launch checklist with the latest stakeholder feedback.",
            "tags": ["launch", "planning", "updated"],
            "category": "PROJECT"
        }
    }
}
```

### Successful Response

```json
{
    "status": "SUCCESS",
    "message": "Memory updated successfully.",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000",
        "version": 2,
        "updated_at": "2026-08-01T12:15:00+00:00"
    }
}
```

---

## DELETE Examples

### Valid Request

```json
{
    "action": "DELETE",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

### Successful Response

```json
{
    "status": "SUCCESS",
    "message": "Memory deleted successfully.",
    "data": {
        "memory_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

---

## LIST Examples

### Valid Request

```json
{
    "action": "LIST",
    "data": {
        "category": "PROJECT",
        "limit": 20,
        "include_deleted": false
    }
}
```

### Successful Response

```json
{
    "status": "SUCCESS",
    "message": "Memories retrieved successfully.",
    "data": {
        "results": [
            {
                "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Launch Planning Notes",
                "category": "PROJECT",
                "created_at": "2026-08-01T12:00:00+00:00",
                "version": 2
            },
            {
                "memory_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "Project Review Agenda",
                "category": "PROJECT",
                "created_at": "2026-08-01T12:30:00+00:00",
                "version": 1
            }
        ]
    }
}
```

---

## Future Write Pipeline

The planned Memory Plugin architecture separates orchestration from execution:

1. An external Orchestrator decides that a memory operation is required.
2. The Orchestrator performs a `SEARCH` operation to locate potentially related memories.
3. Similar memories are returned to the Orchestrator.
4. The Orchestrator decides whether to:
   - `WRITE` a new memory,
   - `UPDATE` an existing memory,
   - ignore the request,
   - or request additional reasoning from another AI component.
5. The Memory Plugin executes only the final command selected by the Orchestrator.

This means the Memory Plugin is an execution service, not a reasoning engine. It stores and retrieves memories as directed, while higher-level intelligence and decision-making remain outside the plugin.
