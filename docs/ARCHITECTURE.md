# Nexus Architecture Report

## 1. Current repository structure

The repository is in an early-stage, plugin-oriented state with a combination of working core plugins, supporting documentation, and experimental or temporary developer artifacts.

```text
Nexus/
├── README.md
├── CHANGELOG.md
├── TODO.md
├── main.py                  # official runtime entry point
├── .gitignore
├── .venv/
├── __pycache__/
├── assets/
│   ├── config.json
│   ├── requirements.txt
│   ├── README.md
│   └── client/
│       └── nexus_connection.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── Memory.md
│   ├── Memory_Examples.md
│   ├── PLUGIN_STANDARD.md
│   └── ...
├── plugins/
│   ├── filesystem/
│   │   ├── actions/
│   │   ├── docs/
│   │   ├── tests/
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── execute.py
│   │   └── filesystem_helpers.py
│   ├── memory/
│   │   ├── actions/
│   │   ├── database/
│   │   ├── docs/
│   │   ├── tests/
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── execute.py
│   │   ├── database.py
│   │   ├── vector_store.py
│   │   ├── get.py
│   │   ├── list.py
│   │   ├── search.py
│   │   ├── write.py
│   │   ├── update.py
│   │   └── delete.py
│   ├── stt/
│   │   ├── actions/
│   │   ├── docs/
│   │   ├── tests/
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── execute.py
│   │   ├── config.py
│   │   ├── model_loader.py
│   │   ├── hardware.py
│   │   ├── stt_helpers.py
│   │   └── config.json
│   └── terminal/
│       ├── actions/
│       ├── docs/
│       ├── tests/
│       ├── README.md
│       ├── __init__.py
│       ├── execute.py
│       ├── process.py
│       ├── process_manager.py
│       ├── terminal_helpers.py
│       └── ...
├── tests/
│   ├── conftest.py
│   ├── test_filesystem.py
│   ├── test_terminal.py
│   ├── test_voice_client.py
│   ├── test_runtime.py
│   ├── dynamic_demo.py
│   ├── dynamic_counter.py
│   └── test.py
├── semantic_search_demo.py
├── filesystem_quickstart.py
├── debug_memory_vector.ipynb
├── tmp-debug-vector.ipynb
└── .pytest_cache/
```

Phase 2 adds the following replaceable intelligence and execution boundaries:

```text
Nexus/
├── orchestrators/
│   ├── base.py              # typed orchestrator contracts
│   ├── dummy.py             # deterministic default brain
│   ├── groq.py              # future Groq implementation slot
│   ├── local.py             # future local-model implementation slot
│   ├── prompt_loader.py     # versioned prompt composition
│   └── prompts/             # editable system/developer/schema instructions
└── runtime/
	├── core.py              # event loop and integration flow
	├── registry.py           # plugin metadata and action discovery
	├── validator.py          # execution-plan structural validation
	└── router.py             # sequential plugin execution
```

## 2. Existing components and responsibilities

### Root-level documents
- README.md: high-level conceptual overview and roadmap.
- TODO.md: backlog and future work items.
- CHANGELOG.md: release history and status notes.
- docs/PLUGIN_STANDARD.md: canonical standard for plugin request/response contracts.

### Plugin layer
- plugins/memory: persistent memory, metadata, category/tag system, optional vector search, SQLite-backed storage.
- plugins/filesystem: CRUD and metadata operations for local files and directories.
- plugins/terminal: managed command execution and process lifecycle control.
- plugins/stt: speech-to-text foundation including hardware detection, model loading, and transcription support.

### Phase 2 orchestration layer
- orchestrators/base.py: standard `OrchestratorContext`, `OrchestratorResult`, `ActionRequest`, `BackgroundTaskRequest`, and `ResponseRequest` models plus the abstract `Orchestrator.process()` interface.
- orchestrators/dummy.py: default deterministic brain. It creates responses and only creates actions explicitly supplied by a caller for deterministic tests.
- orchestrators/groq.py and orchestrators/local.py: documented implementation slots that intentionally do not call a model yet.
- orchestrators/prompt_loader.py and orchestrators/prompts/: version-controlled, readable instruction sources. Runtime metadata can be appended without embedding a large prompt in Python code.
- runtime/registry.py: discovers plugin action names from each plugin's existing `_SUPPORTED_ACTIONS` map and exposes metadata to the validator and future brains.
- runtime/validator.py: checks plan structure, plugin/action references, action data, duplicate IDs, and simple dependencies. It returns valid actions separately when invalid actions are present and reports a `PARTIAL_PLAN` warning.
- runtime/router.py: calls only approved plugin actions in declared sequential order. It converts plugin exceptions and malformed responses into structured action results and continues with independent actions.

### Client and device boundary
- assets/client/nexus_connection.py: HTTP client used by voice/client code to register devices and send user messages to a Nexus server.
- assets/voice_client.py: local client behavior for STT/TTS and server messaging.
- assets/config.json: sample client configuration for network and device settings.

### Tests
- tests/test_filesystem.py: file system plugin integration tests.
- tests/test_terminal.py: terminal execution process tests.
- tests/test_voice_client.py: HTTP and mock transport tests.
- plugin-local tests under plugins/*/tests: validation for each plugin service.
- additional demo scripts and notebooks are present for debugging or experimentation.

## 3. Existing entry points

The authoritative runtime entry point is `main.py`:

```bash
e:/Nexus/.venv/Scripts/python.exe main.py
```

Other entry points include:
- assets/voice_client.py with a client CLI entry point via `main()`.
- semantic_search_demo.py and filesystem_quickstart.py as developer/test scripts.
- plugin-level `execute()` entry points under each plugin package.
- tests and notebooks used during development and debugging.

The voice client remains a client boundary and is not connected directly to the Phase 2 orchestrator.

## 4. Existing plugins

### Memory plugin
Responsibilities:
- persistent memory storage
- SQLite search and retrieval
- optional semantic/vector search
- metadata and tag management
- soft-delete and versioned records

Important constraint:
- It is already a standalone plugin and should remain independent.

### Filesystem plugin
Responsibilities:
- read/write/append/delete/copy/move/list and metadata operations
- standard plugin interface

### Terminal plugin
Responsibilities:
- process execution, lifecycle tracking, and runtime management
- supports dynamic and foreground execution

### STT plugin
Responsibilities:
- model loading and transcription support
- hardware detection
- future voice integration boundary

## 5. Tests and how they are executed

A typical local test workflow uses pytest from the workspace root:

```bash
pytest
```

or a narrower run:

```bash
pytest tests/test_terminal.py -q
pytest tests/test_filesystem.py -q
pytest tests/test_voice_client.py -q
```

The repository also contains plugin-specific tests in subdirectories such as:
- plugins/memory/tests
- plugins/stt/tests
- plugins/terminal/tests
- plugins/filesystem/tests

The current test project already validates the plugin layer and the voice/client transport layer. The runtime layer is not yet implemented, which is why the Phase 1 runtime tests are new.

## 6. Temporary or experimental components

These items are the clearest signs of early, exploratory development:
- tmp-debug-vector.ipynb and debug_memory_vector.ipynb: debugging notebooks for vector memory issues.
- semantic_search_demo.py: demo script for semantic search exploration.
- filesystem_quickstart.py: quick-start script for filesystem behavior.
- dynamic_demo.py and dynamic_counter.py under tests/: demo/test helpers for process behavior rather than production runtime logic.
- multiple docs directories that overlap conceptually and may have drifted from the actual implementation.

These are not automatically harmful, but they indicate the repository needs a clearer boundary between production runtime, plugin code, and developer experiments.

## 7. Proposed Nexus V1 structure

The Phase 1 goal is not to redesign the whole repository. It is to establish a clean runtime layer without breaking the plugin system. The recommended V1 structure is:

```text
Nexus/
├── main.py                  # official runtime entry point
├── runtime/
│   ├── __init__.py
│   ├── core.py
│   ├── registry.py
│   ├── validator.py
│   └── router.py
├── orchestrators/
│   ├── base.py
│   ├── dummy.py
│   ├── groq.py
│   ├── local.py
│   ├── prompt_loader.py
│   └── prompts/
├── plugins/
│   ├── memory/
│   ├── filesystem/
│   ├── terminal/
│   └── stt/
├── assets/
├── docs/
├── tests/
└── README.md
```

The runtime responsibilities are intended to be:
- accept events
- queue them safely
- build context
- route to orchestrator
- log structured results
- keep the process alive without running a continuous LLM loop

The plugin layer remains independent and does not become part of the runtime core logic.

## 8. Duplicate, misplaced, or confusing components

The following are the main confusion points:

1. The repository has a conceptual runtime design in README and TODO, but no actual runtime process exists yet.
2. There are multiple developer-facing scripts and notebooks that overlap with testing or debugging work.
3. The repo includes both plugin-level and repo-level documentation that may drift over time.
4. The voice client and server connection logic live in assets/ instead of a runtime or client boundary layer, which is acceptable for early stages but should remain clearly separated from runtime logic.
5. The concept of an orchestrator exists in the roadmap but not in a dedicated package yet.

## 9. Recommended safe changes

Recommended safe changes for Phase 1 and beyond:

1. Keep the plugin APIs and plugin contracts unchanged.
2. Add a dedicated runtime/ package for event-driven processing.
3. Create a single official startup entry point via main.py.
4. Preserve the Memory, Filesystem, and Terminal plugins as independent capabilities.
5. Keep the runtime event protocol standardized and replaceable.
6. Restrict experimental scripts and notebooks to debugging workflows rather than production paths.
7. Avoid deleting existing files until the runtime layer is proven and tested.
8. Add runtime tests first, then implement only the minimal contract they need.
9. Do not merge Memory into the orchestrator or make the LLM continuously active while idle.

## 10. Architecture summary

The current repo is best described as an early plugin system with a strong conceptual model but without a real runtime loop. The safe and correct next step is to add a minimal runtime layer that handles events, creates context, invokes a dummy orchestrator, and leaves the plugin system intact.

This matches the Phase 1 goal and the Phase 2 goal: establish event-driven structure and a replaceable brain/body boundary without implementing a real LLM.

## 11. Orchestrator contract

Every brain receives an `OrchestratorContext` containing:

- event
- user context
- retrieved memories
- working context
- active tasks
- system context

It returns an `OrchestratorResult` containing status, response metadata, plugin `ActionRequest` items, background task declarations, concise metadata, and an optional structured error. The runtime depends on the abstract `Orchestrator` interface, not on Dummy, Groq, or Local implementations.

An action contains an ID, plugin name, plugin action, dictionary data, and optional `depends_on` IDs. This supports future multi-step plans without introducing a general workflow engine in Phase 2.

## 12. Validator behavior

`ExecutionPlanValidator` is structural validation, not a policy or censorship layer. It verifies registered plugins, discovered actions, required fields, dictionary data, unique IDs, and dependency references. Invalid actions are rejected individually where possible. Valid actions remain in `approved_plan`, while errors identify rejected actions and a `PARTIAL_PLAN` warning explains the result.

## 13. Plugin registry and router

`PluginRegistry` discovers action names from each plugin's existing `_SUPPORTED_ACTIONS` mapping, while preserving the public `execute(request)` entry point. Its metadata includes plugin name, actions, entry point, description, and optional version.

`PluginRouter` executes approved actions sequentially in declared order. It waits for dependency IDs to succeed, records structured results with the original action ID, and continues independent actions after plugin errors. Parallel execution, task scheduling, and policy confirmation are intentionally outside this phase.

## 14. Runtime execution flow

```text
Event
	-> ContextBuilder
	-> Orchestrator.process(context)
	-> ExecutionPlanValidator
	-> PluginRouter
	-> plugin.execute({action, data})
	-> structured Runtime result
```

The runtime result contains `event_id`, `orchestrator_result`, `validation_result`, `execution_results`, `response`, and an overall status. The default Dummy brain produces no actions. Deterministic actions can be injected into it for tests without making normal runtime events execute system operations.

## 15. System instructions and future brains

System, developer, and schema instructions live in `orchestrators/prompts/` and are loaded through `build_system_instruction()`. Runtime information such as available plugin metadata, device information, memories, and active tasks can be appended as structured JSON. A future Groq or local implementation can load these instructions, call its model, parse an `OrchestratorResult`, and be passed to `NexusRuntime(orchestrator=...)` without changing the event queue, validator, router, or plugins.

## 16. Adding an orchestrator implementation

Add a class under `orchestrators/` that subclasses `Orchestrator` and implements:

```python
def process(self, context: OrchestratorContext) -> OrchestratorResult:
		...
```

The implementation should return typed structured data, avoid direct plugin calls, and leave execution to the runtime's validator and router. No separate Conversation AI is required.
