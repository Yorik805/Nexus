# Memory Request Syntax (Memory ISA v1)

The AI communicates with the Memory Plugin using standardized JSON requests.

Every request follows the same structure.

```json
{
    "action": "<operation>",
    "data": {

    }
}
```

---

# Supported Actions

| Action   | Description                    |
| -------- | ------------------------------ |
| `write`  | Create a new memory            |
| `search` | Search existing memories       |
| `update` | Update an existing memory      |
| `delete` | Delete a memory                |
| `get`    | Retrieve a memory using its ID |
| `list`   | List memories matching filters |

---

# 1. WRITE

AI Request

```json
{
    "action": "write",
    "data": {
        "title": "",
        "category": "",
        "content": "",
        "tags": []
    }
}
```

System Automatically Adds

```text
memory_id
created_at
updated_at
version
storage_location
```

---

# 2. SEARCH

AI Request

```json
{
    "action": "search",
    "data": {
        "query": "",
        "category": "",
        "tags": [],
        "limit": 10
    }
}
```

---

# 3. UPDATE

AI Request

```json
{
    "action": "update",
    "data": {
        "memory_id": "",
        "changes": {

        }
    }
}
```

---

# 4. DELETE

AI Request

```json
{
    "action": "delete",
    "data": {
        "memory_id": ""
    }
}
```

---

# 5. GET

AI Request

```json
{
    "action": "get",
    "data": {
        "memory_id": ""
    }
}
```

---

# 6. LIST

AI Request

```json
{
    "action": "list",
    "data": {
        "category": "",
        "tags": []
    }
}
```

---

# Standard Response

Every request returns a standardized response.

```json
{
    "status": "success",
    "message": "",
    "data": {

    }
}
```


# Memory Plugin Interface (Memory ISA v1)

The Memory Plugin communicates only through standardized JSON requests and responses.

---

# Request Format

```json
{
    "action": "",
    "data": {}
}
```

| Field    | Purpose                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------ |
| `action` | The operation the Memory Plugin should perform. (`WRITE`, `SEARCH`, `UPDATE`, `DELETE`, `GET`, `LIST`) |
| `data`   | The information required to perform the selected action. The contents depend on the action.            |

---

# Response Format

```json
{
    "status": "",
    "message": "",
    "data": {}
}
```

| Field     | Purpose                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------- |
| `status`  | Result of the operation. (`SUCCESS` or `ERROR`)                                                   |
| `message` | A short description of the result. Mainly used for logging and debugging.                         |
| `data`    | Contains the requested data, generated information, or additional results returned by the plugin. |

---

# Action Constants

```text
WRITE
SEARCH
UPDATE
DELETE
GET
LIST
```

---

# Status Constants

```text
SUCCESS
ERROR
```

---

# Integration Note

The response from the Memory Plugin is **not** sent directly to the user.

Instead, the Orchestrator collects the outputs from all executed plugins and builds a standardized execution report.

The Conversation AI receives this report as part of its input. Memory results will appear under a dedicated section similar to:

```text
[MEMORY]

...

[/MEMORY]
```

This allows the Conversation AI to understand what memories were found, created, or updated before generating the final response to the user.

The exact execution report format will be defined later in the Runtime/Orchestrator specification.
