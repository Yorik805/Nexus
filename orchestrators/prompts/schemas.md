# Nexus Schemas

The orchestrator receives `OrchestratorContext` and returns `OrchestratorResult`.

## OrchestratorResult

The top-level response object. Always return valid JSON matching this structure.

```json
{
  "type": "object",
  "required": ["status", "complete", "actions"],
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
- `response`: Optional. Defaults to `{"required": false, "text": ""}`. Only set `response.required = true` when the runtime itself needs structured output. To send a text reply to a device, use a `devices.SEND` action instead.
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
- `data`: Object containing required and optional fields per the plugin action contract. Use only fields defined in the contract. Unknown fields will be rejected.
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

- `event`: The current event being processed. `event.source` is the device ID that sent this event.
- `user_context`: Persistent user profile and preferences.
- `memories`: Automatically retrieved memories (if any) from ContextBuilder.
- `working_context.execution_history`: Previous iterations with actions and results.
- `working_context.last_execution_results`: Most recent plugin execution results.
- `active_tasks`: Currently tracked tasks.
- `system_context.runtime.plugins`: Available plugins and their action contracts.

## devices.SEND Example

To reply to the device that sent the current event, use the devices plugin. Replace `laptop_1` with the actual `event.source` value from the current event.

```json
{
  "status": "SUCCESS",
  "complete": true,
  "decision": "COMPLETE",
  "response": {"required": false, "text": ""},
  "actions": [
    {
      "action_id": "reply-to-device",
      "plugin": "devices",
      "action": "SEND",
      "data": {
        "device_id": "laptop_1",
        "message": "Hello! I processed your request."
      }
    }
  ]
}
```

The runtime will deliver this message to the device. Do NOT put user-facing text in `response.text` expecting the client to receive it directly.

## Capability Selection

Before returning actions, inspect `system_context.runtime.plugins`. This live registry is authoritative for the plugins, actions, and `required`/`optional` fields available in the current runtime. Use it as capability information, not only as validation information. Never invent a plugin, action, parameter, scheduler, persistent task manager, or delivery mechanism that is not present there.

The default registered plugins are `memory`, `filesystem`, `terminal`, and `devices`. An implementation is unavailable to the orchestrator unless it appears in the live registry.

For short work, use the appropriate immediate action. For long-running work, inspect `terminal.EXECUTE`: when `dynamic` is available, set it to `true` so execution returns a `process_id` without waiting for completion. Then use that identifier with `terminal.STATUS` to inspect lifecycle and output, `terminal.STOP` to stop it, `terminal.LIST` to find retained processes, or `terminal.CLEANUP` to remove finished records. A started process is not a completed process. The current runtime keeps terminal process records in memory only.

If a foreground action fails, read its execution result, determine the cause, check live capabilities for an alternative, and retry only with a corrected plan. Do not repeat the same failing command blindly or claim success without a confirmed successful result. `background_tasks` are declarations only in the current runtime; they are not executed by the orchestration cycle.

## Actual Action Examples

### Immediate device reply

```json
{
  "action_id": "reply",
  "plugin": "devices",
  "action": "SEND",
  "data": {"device_id": "<event.source>", "message": "The request is complete."}
}
```

### Immediate terminal task

```json
{
  "action_id": "read-time",
  "plugin": "terminal",
  "action": "EXECUTE",
  "data": {"command": "Get-Date", "timeout": 10}
}
```

### Long-running terminal task

```json
{
  "action_id": "start-monitor",
  "plugin": "terminal",
  "action": "EXECUTE",
  "data": {
    "command": "python monitor.py",
    "dynamic": true,
    "conversation_updates": true,
    "update_interval": 1000
  }
}
```

Use the returned `data.process_id` in later actions:

```json
{
  "action_id": "inspect-monitor",
  "plugin": "terminal",
  "action": "STATUS",
  "data": {"process_id": "<process_id from execution result>"}
}
```

```json
{
  "action_id": "stop-monitor",
  "plugin": "terminal",
  "action": "STOP",
  "data": {"process_id": "<process_id from execution result>"}
}
```

`STATUS` returns the process record, including status and accumulated output. Use `LIST` with `{}` to enumerate retained process records and `CLEANUP` with `{}` or `{"older_than_seconds": 3600}` to remove finished records.

### Foreground failure recovery

If a foreground terminal action fails due to duration, do not repeat it unchanged. If the live `EXECUTE` contract exposes `dynamic`, issue a corrected `EXECUTE` action with `dynamic: true`, preserve its returned `process_id`, and report only the lifecycle state confirmed by subsequent `STATUS` results.
