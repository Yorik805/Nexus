from __future__ import annotations

import time

import pytest

from runtime import ContextBuilder, DummyOrchestrator, Event, EventQueue, NexusRuntime


def test_event_creation_and_validation() -> None:
    event = Event(
        event_id="evt-123",
        type="USER_MESSAGE",
        source="test_client",
        data={"text": "Hello Nexus"},
    )
    assert event.event_id == "evt-123"
    assert event.type == "USER_MESSAGE"
    assert event.data["text"] == "Hello Nexus"

    payload = {
        "event_id": "evt-456",
        "type": "USER_MESSAGE",
        "source": "laptop_1",
        "timestamp": "2026-08-25T00:00:00Z",
        "data": {"text": "Hi"},
    }
    restored = Event.from_dict(payload)
    assert restored.event_id == "evt-456"

    with pytest.raises(ValueError):
        Event.from_dict({"type": "UNKNOWN", "source": "x", "data": {}})


def test_event_queue_submission_and_runtime_processing() -> None:
    runtime = NexusRuntime()
    runtime.start()
    try:
        result = runtime.submit_event({
            "type": "USER_MESSAGE",
            "source": "test_client",
            "data": {"text": "Hello Nexus"},
        }, timeout=5.0)
        assert result["status"] == "SUCCESS"
        assert result["event_id"]
        assert result["response"]["text"] == "Dummy orchestrator received your message."
        assert runtime.is_running is True
        assert runtime.last_result["event_id"] == result["event_id"]
        assert len(runtime.event_log) >= 1
    finally:
        runtime.stop()


def test_context_builder_and_dummy_orchestrator_contract() -> None:
    builder = ContextBuilder()
    event = Event(type="USER_MESSAGE", source="client", data={"text": "Hello"})
    context = builder.build(event)

    assert context["event"]["type"] == "USER_MESSAGE"
    assert context["user_context"] == {}
    assert context["memories"] == []
    assert context["active_tasks"] == []

    orchestrator = DummyOrchestrator()
    result = orchestrator.handle(event, context)
    assert result["status"] == "SUCCESS"
    assert result["response"]["text"] == "Dummy orchestrator received your message."


def test_runtime_handles_multiple_events_and_shutdown() -> None:
    runtime = NexusRuntime()
    runtime.start()
    try:
        first = runtime.submit_event({"type": "USER_MESSAGE", "source": "test_a", "data": {"text": "One"}}, timeout=5.0)
        second = runtime.submit_event({"type": "USER_MESSAGE", "source": "test_b", "data": {"text": "Two"}}, timeout=5.0)
        assert first["event_id"] != second["event_id"]
        assert runtime.is_running is True
    finally:
        runtime.stop()

    assert runtime.is_running is False
    assert runtime.shutdown_complete is True


def test_event_queue_basic_behavior() -> None:
    queue = EventQueue()
    event = Event(type="SYSTEM_EVENT", source="ops", data={"message": "started"})
    queue.put(event)
    dequeued = queue.get(timeout=1.0)
    assert dequeued.event_id == event.event_id
    assert dequeued.type == "SYSTEM_EVENT"
    queue.task_done()


def test_runtime_stays_alive_after_event() -> None:
    runtime = NexusRuntime()
    runtime.start()
    try:
        runtime.submit_event({"type": "USER_MESSAGE", "source": "keepalive", "data": {"text": "ping"}}, timeout=5.0)
        time.sleep(0.2)
        assert runtime.is_running is True
    finally:
        runtime.stop()


def test_runtime_event_path_uses_injected_context_builder() -> None:
    calls: list[dict] = []

    class RecordingBuilder(ContextBuilder):
        def build(self, event, **kwargs):
            calls.append({"type": event.type if isinstance(event, Event) else event["type"], "history": kwargs.get("execution_history", [])})
            return super().build(event, **kwargs)

    runtime = NexusRuntime(context_builder=RecordingBuilder(memory_retriever=lambda _text: []))
    runtime.start()
    try:
        result = runtime.submit_event({"type": "USER_MESSAGE", "source": "test", "data": {"text": "hello"}})
    finally:
        runtime.stop()
    assert result["termination_reason"] == "COMPLETED"
    assert calls
    assert calls[0]["type"] == "USER_MESSAGE"


def test_runtime_can_bypass_context_builder_for_all_events() -> None:
    received_contexts: list[object] = []

    class RecordingOrchestrator(DummyOrchestrator):
        def process(self, context):
            received_contexts.append(context)
            return super().process(context)

    runtime = NexusRuntime(
        orchestrator=RecordingOrchestrator(),
        context_builder_enabled=False,
    )
    runtime.start()
    try:
        result = runtime.submit_event({"type": "USER_MESSAGE", "source": "test", "data": {"text": "hello"}})
    finally:
        runtime.stop()

    assert result["status"] == "SUCCESS"
    assert runtime.context_builder is None
    assert len(received_contexts) == 1
    assert received_contexts[0].event["data"] == {"text": "hello"}
    assert received_contexts[0].memories == []
    assert received_contexts[0].working_context["execution_history"] == []


def test_runtime_reads_numeric_context_builder_switch(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_CONTEXT_BUILDER_ENABLED", "0")

    runtime = NexusRuntime(orchestrator=DummyOrchestrator())

    assert runtime.context_builder_enabled is False
    assert runtime.context_builder is None
