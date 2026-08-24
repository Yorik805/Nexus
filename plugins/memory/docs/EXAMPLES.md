# Memory Plugin Examples (v2)

## SQLITE example

Find project named CPU:

```json
{
  "action": "SEARCH",
  "data": {
    "type": "SQLITE",
    "query": "CPU",
    "category": "PROJECT"
  }
}
```

## VECTOR example

Find a memory by natural language:

```json
{
  "action": "SEARCH",
  "data": {
    "type": "VECTOR",
    "query": "What was that day I felt sick?",
    "limit": 5
  }
}
```

Use `VECTOR` for natural language lookups and `SQLITE` for exact, structured queries.
