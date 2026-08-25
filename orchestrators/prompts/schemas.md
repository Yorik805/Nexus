# Nexus Schemas

The orchestrator receives `OrchestratorContext` and returns `OrchestratorResult`.

An action contains `action_id`, `plugin`, `action`, `data`, and optional `depends_on`. Action data is always an object. Plugin execution returns a structured status, message, and data payload. Runtime execution results associate each plugin response with the original action ID.
