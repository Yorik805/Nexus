from __future__ import annotations

import threading
import uuid
from concurrent.futures import Future
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any

VALID_EVENT_TYPES = {
    "USER_MESSAGE",
    "SYSTEM_EVENT",
    "TASK_EVENT",
    "TIMER_EVENT",
    "PLUGIN_EVENT",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


class PluginRegistry:
    """Minimal plugin registry for the first runtime pass."""

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}
        self.register("memory", self._load_plugin("plugins.memory"))
        self.register("filesystem", self._load_plugin("plugins.filesystem"))
        self.register("terminal", self._load_plugin("plugins.terminal"))

    def _load_plugin(self, module_name: str) -> Any:
        module = __import__(module_name, fromlist=["execute"])
        return getattr(module, "execute", None)

    def register(self, name: str, handler: Any) -> None:
        self._plugins[str(name).lower()] = handler

    def get_plugin(self, name: str) -> Any:
        return self._plugins.get(str(name).lower())

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins)


class ContextBuilder:
    """Placeholder context builder for the runtime contract."""

    def build(self, event: Event) -> dict[str, Any]:
        # Phase 1 placeholder contract: keep the context intentionally minimal.
        # Memory relevance, user preferences, and active task intelligence are
        # added deliberately later without changing the runtime interface.
        return {
            "event": event.to_dict(),
            "user_context": {},
            "memories": [],
            "working_context": {},
            "active_tasks": [],
        }


class DummyOrchestrator:
    """Placeholder orchestrator for event-driven runtime validation."""

    def handle(self, event: Event, context: dict[str, Any]) -> dict[str, Any]:
        if event.type == "USER_MESSAGE":
            response_text = "Dummy orchestrator received your message."
        else:
            response_text = "Dummy orchestrator processed a non-user event."

        return {
            "status": "SUCCESS",
            "event_id": event.event_id,
            "actions": [],
            "response": {"text": response_text},
            "context": context,
        }


class NexusRuntime:
    """Minimal always-on runtime that waits for events and processes them."""

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self.registry = plugin_registry or PluginRegistry()
        self.queue = EventQueue()
        self.event_log: list[dict[str, Any]] = []
        self._thread: threading.Thread | None = None
        self.is_running = False
        self.shutdown_complete = False
        self.last_result: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._future_map: dict[str, Future] = {}
        self.context_builder = ContextBuilder()
        self.orchestrator = DummyOrchestrator()

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
            finally:
                self.queue.task_done()

        self.shutdown_complete = True

    def _process_event(self, event: Event) -> dict[str, Any]:
        context = self.context_builder.build(event)
        result = self.orchestrator.handle(event, context)
        result["event_id"] = event.event_id
        result["response"] = result.get("response", {})
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
