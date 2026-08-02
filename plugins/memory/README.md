# Memory Plugin

The Memory Plugin is the central storage and retrieval system for Nexus.

It provides a structured way to store, search, update, and manage memories with support for categorization, tagging, versioning, and soft deletion.

## Supported Actions

- **WRITE** — Store a new memory
- **SEARCH** — Find memories by query, category, or tags
- **GET** — Retrieve a complete memory record
- **UPDATE** — Modify an existing memory
- **DELETE** — Soft delete a memory
- **LIST** — List memories with filtering

## Key Features

- SQLite-backed persistent storage
- Automatic UUID generation for each memory
- ISO 8601 timestamps (UTC)
- Version tracking for updates
- Soft deletion (recoverable)
- Predefined categories: PROJECT, PERSON, IDEA, PREFERENCE
- Tag-based organization
- Lightweight search results (no full content in searches)
- Complete record retrieval with GET
- Safe schema migration for new deployments

## Usage

All interactions with the Memory Plugin go through the standard `execute()` function:

```python
from plugins.memory.execute import execute

response = execute({
    "action": "WRITE",
    "data": {
        "title": "My Memory",
        "category": "PROJECT",
        "content": "...",
        "tags": ["tag1", "tag2"]
    }
})
```

## API Reference

See [/docs/Memory_Examples.md](../../../docs/Memory_Examples.md) for complete request/response examples.

## Database

The Memory Plugin uses SQLite with automatic initialization at `plugins/memory/database/memory.db`.

The database schema includes:
- `memory_id` — Unique identifier (UUID)
- `title` — Memory title
- `category` — One of PROJECT, PERSON, IDEA, PREFERENCE
- `content` — Full content
- `tags` — JSON-encoded array of tags
- `created_at` — Creation timestamp
- `updated_at` — Last update timestamp
- `version` — Integer version counter
- `deleted` — Soft delete flag
- `deleted_at` — Deletion timestamp (for auditing)

## Plugin Standard

This plugin complies with the [Nexus Plugin Standard](/docs/PLUGIN_STANDARD.md).
