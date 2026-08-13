import logging

import pytest

from agent_arena import event_bus
from agent_arena.battles import merge_new_events, sse_message, _is_terminal_event


class _FlakyDatabases:
    def __init__(self, fail_times: int, duplicate_on: int | None = None):
        self.fail_times = fail_times
        self.duplicate_on = duplicate_on
        self.calls = 0
        self.docs: list[tuple] = []

    def create_document(self, database_id, collection, doc_id, payload):
        self.calls += 1
        if self.duplicate_on is not None and self.calls == self.duplicate_on:
            from appwrite.exception import AppwriteException

            raise AppwriteException("already exists", 409, "document_already_exists")
        if self.calls <= self.fail_times:
            raise RuntimeError("simulated appwrite failure")
        self.docs.append((doc_id, payload))
        return None


def _stub_db(monkeypatch, fail_times: int, duplicate_on: int | None = None):
    from agent_arena import db

    fake = _FlakyDatabases(fail_times, duplicate_on=duplicate_on)
    monkeypatch.setattr(db, "get_databases", lambda: fake)
    monkeypatch.setattr(db, "get_database_id", lambda: "test-db")
    monkeypatch.setattr(event_bus, "_sleep", lambda _s: None)
    return fake


def _ev(event_id: str = "ev1") -> dict:
    return {
        "event_id": event_id,
        "type": "artifact",
        "data": {"phase": "p", "model_id": "m", "artifact": "a"},
        "created_at": 1.0,
    }


def test_persist_one_retries_then_succeeds(monkeypatch):
    fake = _stub_db(monkeypatch, fail_times=3)
    event_bus._persist_one("battle-1", _ev())
    assert fake.calls == 4


def test_persist_one_raises_after_all_retries(monkeypatch):
    fake = _stub_db(monkeypatch, fail_times=99)
    with pytest.raises(RuntimeError):
        event_bus._persist_one("battle-1", _ev())
    assert fake.calls == 4


def test_persist_duplicate_treated_as_success(monkeypatch):
    fake = _stub_db(monkeypatch, fail_times=0, duplicate_on=1)
    event_bus._persist_one("battle-1", _ev("dup-id-1"))
    assert fake.calls == 1


def test_persist_or_log_failure_without_daemon(monkeypatch):
    _stub_db(monkeypatch, fail_times=99)
    seen: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())

    handler = _Capture()
    logger = logging.getLogger("agent_arena.event_bus")
    logger.addHandler(handler)
    try:
        event_bus._persist_or_log("battle-1", _ev())
    finally:
        logger.removeHandler(handler)
    assert any("durable event persist failed" in s and "battle-1" in s for s in seen)


def test_publish_enqueues_durable_write(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        event_bus,
        "_persist_async",
        lambda battle_id, event: calls.append((battle_id, event)),
    )
    enriched = event_bus.publish("battle-q", {"type": "artifact", "data": {"x": 1}})
    assert event_bus._DOC_ID_RE.match(enriched["event_id"])
    assert enriched["created_at"]
    assert len(calls) == 1


def test_load_durable_raises_typed_error(monkeypatch):
    from agent_arena import db

    def boom(*a, **k):
        raise RuntimeError("appwrite down")

    monkeypatch.setattr(db, "get_databases", boom)
    with pytest.raises(event_bus.DurableReadError):
        event_bus.load_durable("b")


def test_merge_dedupes_and_orders_mixed_local_durable():
    seen: set[str] = set()
    durable = [
        {"event_id": "b", "created_at": 2.0, "type": "artifact", "data": {"n": 2}},
        {"event_id": "a", "created_at": 1.0, "type": "artifact", "data": {"n": 1}},
    ]
    local = [
        {"event_id": "a", "created_at": 1.0, "type": "artifact", "data": {"n": 1}},
        {"event_id": "c", "created_at": 3.0, "type": "artifact", "data": {"n": 3}},
    ]
    merged = merge_new_events(local, durable, seen)
    assert [e["event_id"] for e in merged] == ["a", "b", "c"]
    merged2 = merge_new_events(local, durable, seen)
    assert merged2 == []


def test_sse_payload_includes_event_id():
    msg = sse_message(
        {"type": "artifact", "event_id": "eid", "created_at": 1.5, "data": {"x": 1}}
    )
    assert msg["event"] == "artifact"
    assert '"event_id": "eid"' in msg["data"]
    assert '"created_at": 1.5' in msg["data"]


def test_terminal_event_detection():
    assert _is_terminal_event({"type": "battle_status", "data": {"status": "completed"}})
    assert not _is_terminal_event({"type": "artifact", "data": {"status": "completed"}})
