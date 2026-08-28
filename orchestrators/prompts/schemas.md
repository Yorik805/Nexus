# Nexus Schemas

The orchestrator receives `OrchestratorContext` and returns `OrchestratorResult`.

## OrchestratorResult

The top-level response object. Always return valid JSON matching this structure.

```json
{
  "type": "object",
  "required": ["status", "complete", "response", "actions"],
  "properties": {
    "status": {"type": "string", "enum": ["SUCCESS", "ERROR", "PARTIAL_SUCCESS"]},
    "complete": {"type": "boolean"},
    "decision": {"type": "string", "enum": ["CONTINUE", "NO_ACTION", "COMPLETE"]},
    "response": {
      "type": "object",
      "required": ["required", "text"],
      "properties": {
        "required": {"type": "boolean"},
        "text": {"type": "string"},
        "metadata": {"type": "object"}
      }
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["action_id", "plugin", "action", "data"],
        "properties": {
          "action_id": {"type": "string"},
          "plugin": {"type": "string"},
          "action": {"type": "string"},
          "data": {"type": "object"},
          "depends_on": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "background_tasks": {"type": "array", "items": {"type": "object"}},
    "metadata": {"type": "object"},
    "error": {"type": "object"}
  }
}
```

### Field Details

- `status`: Overall result status. Use `SUCCESS` when the plan is valid and ready for execution. Use `ERROR` when the orchestrator itself cannot produce a valid plan.
- `complete`: `true` only when the user's request is fully satisfied. Never infer completion from an empty action list.
- `decision`: `CONTINUE` when more work is required, `NO_ACTION` when nothing should execute, `COMPLETE` when finished.
- esponse: Internal output. Set equired=false unless the runtime itself needs structured output. To send a text reply to a device, use a devices.SEND action instead.
- `actions`: Ordered list of plugin operations to execute. Each action is an `ActionRequest`.
- `background_tasks`: Declarations of deferred work. These are declarations only; do not expect them to execute yet.
- `metadata`: Optional structured metadata (intent, plan fingerprint, etc.).
- `error`: Optional structured error object with `code` and `message`.

## ActionRequest

Each item in the `actions` array.

```json
{
  "type": "object",
  "required": ["action_id", "plugin", "action", "data"],
  "properties": {
    "action_id": {"type": "string"},
    "plugin": {"type": "string"},
    "action": {"type": "string"},
    "data": {"type": "object"},
    "depends_on": {"type": "array", "items": {"type": "string"}}
  }
}
```

### Field Details

- `action_id`: Unique string identifier for this action. Used to correlate execution results back to the action.
- `plugin`: Must be one of the plugin names provided in `runtime.plugins`.
- `action`: Must be one of the actions listed in that plugin's contracts.
- `data`: Object containing required and optional fields per the plugin action contract. Use only fields defined in the contract.
- `depends_on`: Optional array of `action_id` strings. Actions listed here must succeed before this action executes.

## OrchestratorContext

The input you receive. For reference only; do not return this structure.

```json
{
  "type": "object",
  "required": ["event"],
  "properties": {
    "event": {
      "type": "object",
      "required": ["event_id", "type", "source", "data"],
      "properties": {
        "event_id": {"type": "string"},
        "type": {"type": "string"},
        "source": {"type": "string"},
        "data": {"type": "object"},
        "timestamp": {"type": "string"}
      }
    },
    "user_context": {"type": "object"},
    "memories": {"type": "array", "items": {"type": "object"}},
    "working_context": {
      "type": "object",
      "properties": {
        "execution_history": {"type": "array", "items": {"type": "object"}},
        "last_execution_results": {"type": "array", "items": {"type": "object"}}
      }
    },
    "active_tasks": {"type": "array", "items": {"type": "object"}},
    "system_context": {
      "type": "object",
      "properties": {
        "runtime": {
          "type": "object",
          "properties": {
            "plugins": {"type": "object"}
          }
        }
      }
    }
  }
}
```

### Field Details

- `event`: The current event being processed.
- `user_context`: Persistent user profile and preferences.
- `memories`: Automatically retrieved memories (if any) from ContextBuilder.
- `working_context.execution_history`: Previous iterations with actions and results.
- `working_context.last_execution_results`: Most recent plugin execution results.
- `active_tasks`: Currently tracked tasks.
- `system_context.runtime.plugins`: Available plugins and their action contracts.
## devices.SEND Example

To reply to the device that sent the current event, use the devices plugin:

```json
{
  "decision": "COMPLETE",
  "actions": [
    {
      "action_id": "reply-to-device",
      "plugin": "devices",
      "action": "SEND",
      "data": {
        "device_id": "<event.source>",
        "message": "Your reply text here"
      }
    }
  ]
}
```

The `device_id` should match the `source` field of the current event. The runtime will deliver the message to that device.
To reply to the device that sent the current event, use the devices plugin:

```json
{
  "decision": "COMPLETE",
  "actions": [
    {
      "action_id": "reply-to-device",
      "plugin": "devices",
      "action": "SEND",
      "data": {
        "device_id": "<event.source>",
        "message": "Your reply text here"
      }
    }
  ]
}
```

The `device_id` should match the `source` field of the current event. The runtime will deliver the message to that device.
