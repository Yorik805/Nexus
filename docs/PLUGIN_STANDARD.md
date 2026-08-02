# Nexus Plugin Standard

This document defines the official contract and standard that every plugin in Nexus must follow.

---

## Plugin Philosophy

Every capability in Nexus is implemented as a plugin. Plugins are independent, single-purpose modules that integrate into the Nexus ecosystem through a standardized interface.

### Core Principles

- **Every capability is a plugin** — The system is built from plugins, not the other way around.
- **Plugins never talk directly to each other** — All inter-plugin communication flows through the Orchestrator.
- **Plugins never communicate with the user** — User interaction is handled by the Orchestrator and Conversation Engine.
- **Plugins perform one job well** — Each plugin has a single, well-defined responsibility.
- **Plugins return structured results** — All responses follow the standard format.
- **The Orchestrator decides** — Only the Orchestrator decides which plugin to call and how to use the results.

This design ensures plugins remain decoupled, testable, and reusable across different Nexus deployments.

---

## Folder Structure

Every plugin must follow this standardized directory structure:

```
plugins/
    plugin_name/
        execute.py           # Main entry point (mandatory)
        __init__.py          # Package initialization
        README.md            # Plugin documentation
        
        actions/             # Individual action modules
            action_one.py
            action_two.py
            ...
        
        docs/                # Extended documentation
            ARCHITECTURE.md
            EXAMPLES.md
            ...
        
        tests/               # Test suite
            test_action_one.py
            test_action_two.py
            ...
```

### File and Folder Purposes

- **execute.py** — Main entry point that exposes the `execute(request: dict) -> dict` function. Dispatches requests to the appropriate action.

- **__init__.py** — Package initializer. Should expose `execute` so plugins can be imported cleanly.

- **README.md** — User-facing documentation describing what the plugin does, its actions, and basic usage examples.

- **actions/** — Directory containing one module per action. Each module exports a single function matching the action name. Keeps logic modular and testable.

- **docs/** — Extended documentation for developers. May include architecture diagrams, implementation notes, or detailed examples.

- **tests/** — Test suite. Should test each action independently and cover edge cases, validation, and error conditions.

---

## Standard Execute Interface

Every plugin must expose exactly one public function:

```python
def execute(request: dict) -> dict:
    """Execute a plugin action.
    
    Args:
        request: Dictionary with "action" and "data" keys.
    
    Returns:
        Standard response dictionary.
    """
    ...
```

This function is **mandatory** and is the only entry point into the plugin.

The `execute` function must:

- Accept a request dictionary
- Validate the request structure
- Dispatch to the appropriate action handler
- Return a standardized response
- Never raise an exception (handle all errors gracefully)

---

## Standard Request Format

All requests to any plugin follow this format:

```json
{
    "action": "ACTION_NAME",
    "data": { ... }
}
```

### Fields

- **action** — A string identifying which operation to perform. Determines which handler is called. Must be uppercase.

- **data** — A dictionary containing the parameters for the action. Structure varies by action. Can be empty.

### Example

```json
{
    "action": "WRITE",
    "data": {
        "title": "My Note",
        "content": "...",
        "tags": ["important"]
    }
}
```

---

## Standard Response Format

All responses from any plugin follow this format:

```json
{
    "status": "SUCCESS" or "ERROR",
    "message": "Human-readable description",
    "data": { ... }
}
```

### Fields

- **status** — Either `"SUCCESS"` or `"ERROR"`. Indicates whether the operation succeeded.

- **message** — A human-readable string describing the result. For errors, this should clearly explain what went wrong. For success, this confirms what was done.

- **data** — A dictionary containing the result. On success, contains the operation's output (IDs, records, etc.). On error, should be empty (`{}`).

### Examples

**Success:**
```json
{
    "status": "SUCCESS",
    "message": "Record created successfully.",
    "data": {
        "id": "123",
        "created_at": "2026-08-02T12:00:00Z"
    }
}
```

**Error:**
```json
{
    "status": "ERROR",
    "message": "Invalid input: title cannot be empty.",
    "data": {}
}
```

---

## Error Handling

Plugins must be robust and never crash. Follow these rules:

- **Validate all inputs** — Check types, formats, and required fields before processing.

- **Return ERROR responses** — Use the standard response format. Never raise exceptions.

- **Human-readable messages** — Error messages should clearly explain what was wrong and how to fix it.

- **Never return partial data** — If any operation fails, return an empty `data` object. Do not return incomplete results.

- **Graceful degradation** — If a non-critical operation fails, handle it gracefully. Only fail the entire request if necessary.

### Example Error Flow

```python
def execute(request: dict) -> dict:
    if not isinstance(request, dict):
        return {
            "status": "ERROR",
            "message": "Request must be a dictionary.",
            "data": {}
        }
    
    action = request.get("action")
    if action not in SUPPORTED_ACTIONS:
        return {
            "status": "ERROR",
            "message": f"Unsupported action: {action}",
            "data": {}
        }
    
    # Process...
```

---

## Logging

Plugins should be easy to debug and monitor. While centralized logging is not yet implemented, plugins should:

- Use clear, descriptive error messages
- Include context in responses
- Support debug output (future feature)
- Avoid noisy logging

Future versions of Nexus may include centralized logging infrastructure that all plugins will tap into.

---

## Plugin Independence

Plugins operate in isolation and communicate only through the Orchestrator:

- **No direct imports** — Plugins should never import or call other plugins directly.

- **No shared state** — Plugins do not maintain state that other plugins depend on.

- **No hardcoded dependencies** — Plugins do not assume the presence of other plugins.

- **Request/response only** — All interaction is through the standard request/response format.

This ensures plugins remain:
- Independently testable
- Easily replaceable
- Portable across systems
- Free from circular dependencies

---

## Versioning

Every plugin has an independent version that evolves separately:

- Plugins are versioned independently of Nexus.
- Breaking changes to a plugin's interface should increment the major version.
- Plugins should maintain backward compatibility when possible.
- The Orchestrator may manage multiple plugin versions simultaneously.

---

## Future Compatibility

This interface is designed to remain stable as plugins become more sophisticated:

- New actions can be added without breaking existing ones
- Response format may expand but will remain backward-compatible
- The core `execute(request) -> dict` contract will not change
- Plugins can add optional fields to responses as features evolve

Plugins should be designed with extensibility in mind, allowing for future enhancements without requiring rewrites.

---

## Summary

A compliant Nexus plugin is:

1. ✅ Self-contained with a clear folder structure
2. ✅ Accessed only through `execute(request: dict) -> dict`
3. ✅ Communicates via standardized request/response format
4. ✅ Handles all errors gracefully
5. ✅ Independent and never imports other plugins
6. ✅ Well-documented and tested
7. ✅ Ready to be called by the Orchestrator

Following this standard ensures Nexus remains modular, scalable, and maintainable as it grows.
