# Memory Plugin API (v2)

SEARCH action now requires a `type` field and supports two modes:

Request format:

```json
{
  "action": "SEARCH",
  "data": {
    "type": "SQLITE" | "VECTOR",
    "query": "...",
    "category": "...",
    "tags": ["..."],
    "limit": 10,
    "include_deleted": false
  }
}
```

- `type` (required): `SQLITE` runs the existing SQLite-based keyword search. `VECTOR` runs semantic search using embeddings.
- `include_deleted`: when `VECTOR` is used, deleted memories are excluded by default; set `include_deleted: true` to include them.

Response format remains unchanged and returns `results` as a list of lightweight records.
