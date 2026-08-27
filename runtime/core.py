from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import Future
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any, Callable

from orchestrators import Orchestrator, OrchestratorContext, create_orchestrator

from .registry import PluginRegistry
from .orchestration_cycle import OrchestrationCycle, OrchestrationCycleConfig
from .router import PluginRouter
from .validator import ExecutionPlanValidator
from .observability import RuntimeTrace

VALID_EVENT_TYPES = {
    "USER_MESSAGE",
    "SYSTEM_EVENT",
    "TASK_EVENT",
    "TIMER_EVENT",
    "PLUGIN_EVENT",
    "EXECUTION_RESULT",
    "BACKGROUND_TASK_RESULT",
    "ERROR",
    "TIMER",
    "INTERNAL",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def context_builder_enabled_from_environment() -> bool:
    """Return whether event enrichment is enabled for this runtime process.

    ``NEXUS_CONTEXT_BUILDER_ENABLED=0`` is useful on constrained local-model
    hosts where the raw event should go directly to the orchestrator.  The
    setting is deliberately server-side: a client must not be able to disable
    memory/context enrichment for every other client.
    """
    value = os.getenv("NEXUS_CONTEXT_BUILDER_ENABLED", "1").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        "NEXUS_CONTEXT_BUILDER_ENABLED must be one of: 1, 0, true, false, yes, no, on, off."
    )


class Event:
    """Simple event object used by the Nexus runtime."""

    def __init__(
        self,
        event_id: str | None = None,
        type: str = "SYSTEM_EVENT",
        source: str = "unknown",
        timestamp: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        event_type = str(type).strip().upper()
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {type!r}")
        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")

        self.event_id = str(event_id or uuid.uuid4())
        self.type = event_type
        self.source = str(source)
        self.timestamp = timestamp or utc_now_iso()
        self.data = dict(data)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Event":
        if not isinstance(payload, dict):
            raise ValueError("Event payload must be a dictionary.")

        event_type = str(payload.get("type", "")).strip().upper()
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {payload.get('type')!r}")

        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")

        return cls(
            event_id=payload.get("event_id"),
            type=event_type,
            source=str(payload.get("source", "unknown")),
            timestamp=payload.get("timestamp"),
            data=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.type,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": dict(self.data),
        }


class EventQueue:
    """Thread-safe in-process event queue."""

    def __init__(self) -> None:
        self._queue: Queue[Event | None] = Queue()

    def put(self, event: Event | None) -> None:
        self._queue.put(event)

    def get(self, timeout: float | None = None) -> Event | None:
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        self._queue.task_done()


class ContextBuilder:
    """Enrich raw events before they reach the orchestrator."""

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        user_context_provider: Callable[[Event], dict[str, Any]] | None = None,
        memory_retriever: Callable[[str], list[dict[str, Any]]] | None = None,
        trace: RuntimeTrace | None = None,
    ) -> None:
        self.registry = registry or PluginRegistry()
        self.user_context_provider = user_context_provider or (lambda _event: {})
        self.memory_retriever = memory_retriever or self._retrieve_memories
        self.trace = trace

    def build(
        self,
        event: Event | dict[str, Any],
        execution_state: dict[str, Any] | None = None,
        execution_history: list[dict[str, Any]] | None = None,
        runtime_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_type = event.type if isinstance(event, Event) else str(event.get("type", "")).upper()
        event_data = event.to_dict() if isinstance(event, Event) else dict(event)
        event_object = event if isinstance(event, Event) else Event.from_dict(event_data)
        if self.trace:
            self.trace.record("context_builder.start", event_object.event_id, event_type=event_type)
        memories: list[dict[str, Any]] = []
        memory_metadata: dict[str, Any] = {"status": "not_applicable", "count": 0}
        if event_type == "USER_MESSAGE":
            text = event_object.data.get("text", "")
            if isinstance(text, str) and text.strip():
                try:
                    memories = self.memory_retriever(text)
                    memory_metadata = {"status": "success" if memories else "empty", "count": len(memories)}
                except Exception as exc:
                    memory_metadata = {"status": "failed", "count": 0, "error": str(exc)}
        context_sources = ["event", "execution_history", "runtime_state"]
        if memory_metadata["status"] == "success":
            context_sources.append("memory")
        if self.trace:
            self.trace.record("context_builder.complete", event_object.event_id, event_type=event_type, memory_status=memory_metadata["status"], memory_count=memory_metadata["count"], context_sources=context_sources, history_count=len(execution_history or []))
        built_context = {
            "event": event_data,
            "user_context": self.user_context_provider(event_object),
            "memories": memories,
            "working_context": {
                "execution_state": execution_state or {},
                "execution_history": execution_history if isinstance(execution_history, list) else (execution_history or {}).get("recent_execution_history", []),
                "history_context": execution_history if isinstance(execution_history, dict) else {},
            },
            "active_tasks": [],
            "system_context": {
                "context_metadata": {
                    "context_sources": context_sources,
                    "memory": memory_metadata,
                },
                "runtime_state": runtime_state or {},
            },
        }
        if self.trace:
            self.trace.record(
                "context_builder.output",
                event_object.event_id,
                context_keys=sorted(built_context),
                event_type=event_type,
                memory_status=memory_metadata["status"],
                memory_count=memory_metadata["count"],
                execution_history_count=len(built_context["working_context"]["execution_history"]),
                runtime_state_keys=sorted((runtime_state or {}).keys()),
            )
        return built_context

    def _retrieve_memories(self, text: str) -> list[dict[str, Any]]:
        plugin = self.registry.get("memory")
        if plugin is None:
            raise RuntimeError("Memory plugin is unavailable.")
        response = plugin.entry_point({"action": "SEARCH", "data": {"type": "SQLITE", "query": text, "limit": 5}})
        if not isinstance(response, dict) or response.get("status") != "SUCCESS":
            raise RuntimeError(str(response.get("message", "Memory retrieval failed.")) if isinstance(response, dict) else "Memory retrieval failed.")
        data = response.get("data", {})
        return data.get("results", []) if isinstance(data, dict) and isinstance(data.get("results", []), list) else []


class NexusRuntime:
    """Minimal always-on runtime that waits for events and processes them."""

    def __init__(
        self,
        plugin_registry: PluginRegistry | None = None,
        orchestrator: Orchestrator | None = None,
        context_builder: ContextBuilder | None = None,
        context_builder_enabled: bool | None = None,
        log_path: str = "logs/nexus_runtime.log",
    ) -> None:
        self.registry = plugin_registry or PluginRegistry()
        self.queue = EventQueue()
        self.event_log: list[dict[str, Any]] = []
        self._thread: threading.Thread | None = None
        self.is_running = False
        self.shutdown_complete = False
        self.last_result: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._future_map: dict[str, Future] = {}
        self.trace = RuntimeTrace(log_path)
        self.context_builder_enabled = (
            context_builder_enabled
            if context_builder_enabled is not None
            else context_builder_enabled_from_environment()
        )
        self.context_builder = (
            context_builder
            if self.context_builder_enabled
            else None
        )
        if self.context_builder is None and self.context_builder_enabled:
            self.context_builder = ContextBuilder(self.registry, trace=self.trace)
        self.orchestrator = orchestrator or create_orchestrator(trace=self.trace.record)
        self.cycle_config = OrchestrationCycleConfig()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.shutdown_complete = False
            self._thread = threading.Thread(target=self._event_loop, name="nexus-runtime", daemon=True)
            self._thread.start()
        print("Nexus Runtime starting...")
        print("Loading configuration...")
        print("Loading plugin registry...")
        print("Starting event system...")
        print("Nexus is online.")
        print("Waiting for events...")

    def submit_event(self, payload: dict[str, Any], timeout: float | None = 5.0) -> dict[str, Any]:
        if not self.is_running:
            self.start()

        event = Event.from_dict(payload)
        self.trace.record("event.received", event.event_id, event_type=event.type, source=event.source)
        future: Future = Future()
        with self._lock:
            self._future_map[event.event_id] = future
        self.queue.put(event)

        try:
            result = future.result(timeout=timeout)
        except TimeoutError as exc:
            raise TimeoutError(f"Event {event.event_id} was not processed within {timeout} seconds.") from exc
        finally:
            with self._lock:
                self._future_map.pop(event.event_id, None)

        return result

    def _event_loop(self) -> None:
        while self.is_running:
            try:
                item = self.queue.get(timeout=0.25)
            except Empty:
                continue

            if item is None:
                self.queue.task_done()
                break

            try:
                result = self._process_event(item)
                future = self._future_map.get(item.event_id)
                if future is not None and not future.done():
                    future.set_result(result)
                self.last_result = result
                self.event_log.append({
                    "event_id": item.event_id,
                    "type": item.type,
                    "status": result.get("status", "SUCCESS"),
                    "timestamp": item.timestamp,
                })
                self.trace.record("event.complete", item.event_id, event_type=item.type, status=result.get("status"), termination_reason=result.get("termination_reason"))
            finally:
                self.queue.task_done()

        self.shutdown_complete = True

    def _process_event(self, event: Event) -> dict[str, Any]:
        self.trace.record("cycle.start", event.event_id, event_type=event.type)
        context = OrchestratorContext(
            event=event.to_dict(),
            system_context={"runtime": {"plugins": self.registry.metadata()}},
        )
        cycle = OrchestrationCycle(
            self.orchestrator,
            ExecutionPlanValidator(self.registry),
            PluginRouter(self.registry),
            self.cycle_config,
            context_builder=self.context_builder.build if self.context_builder is not None else None,
            trace=self.trace,
        )
        result = cycle.run(context)
        self.trace.record("cycle.complete", event.event_id, status=result.get("status"), termination_reason=result.get("termination_reason"), iterations=result.get("iterations"))
        return result

    def stop(self) -> None:
        if not self.is_running:
            return

        self.is_running = False
        self.queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        print("Nexus Runtime stopped.")


if __name__ == "__main__":
    runtime = NexusRuntime()
    runtime.start()
    try:
        while runtime.is_running:
            import time
            time.sleep(0.25)
    except KeyboardInterrupt:
        runtime.stop()
