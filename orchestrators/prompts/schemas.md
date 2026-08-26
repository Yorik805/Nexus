# Nexus Schemas

The orchestrator receives `OrchestratorContext` and returns `OrchestratorResult`.

An action contains `action_id`, `plugin`, `action`, `data`, and optional `depends_on`. Action data is always an object. Plugin execution returns a structured status, message, and data payload. Runtime execution results associate each plugin response with the original action ID. Set `complete` to false when another decision is required and true only when the task is finished; do not infer completion only from an empty action list.
