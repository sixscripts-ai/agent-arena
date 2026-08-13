import importlib.util
import json
import sys
import threading
import time
from types import ModuleType

import pytest
from appwrite.query import Query

from agent_arena import db
from agent_arena.battles import merge_new_events
from tests.conftest import make_user_id, requires_appwrite


@pytest.fixture(autouse=True)
def _stub_leaderboard(monkeypatch):
    try:
        spec = importlib.util.find_spec("agent_arena.leaderboard")
    except ModuleNotFoundError:
        spec = None
    if spec is not None:
        return
    stub = ModuleType("agent_arena.leaderboard")
    stub.apply_result = lambda databases, database_id, format_id, model_ids, scores: (
        None
    )
    monkeypatch.setitem(sys.modules, "agent_arena.leaderboard", stub)


def _real_format_id() -> str:
    databases = db.get_databases()
    res = databases.list_documents(
        db.get_database_id(), "formats", queries=[Query.limit(1)]
    )
    assert res.documents, "formats collection is empty; seed it first (Task 6)"
    return res.documents[0].id


@pytest.fixture(autouse=True)
def _fast_sse_drain(monkeypatch):
    monkeypatch.setattr("agent_arena.battles._SSE_DRAIN_SECONDS", 0.0)
    monkeypatch.setattr("agent_arena.battles._DURABLE_RELOAD_INTERVAL", 0.05)


def test_reconnect_replays_full_history():
    history = [
        {"event_id": "1", "created_at": 1.0, "type": "phase_start", "data": {"phase": "p"}},
        {"event_id": "2", "created_at": 2.0, "type": "artifact", "data": {"artifact": "x"}},
        {"event_id": "3", "created_at": 3.0, "type": "battle_status", "data": {"status": "completed"}},
    ]
    first = merge_new_events([], history, set())
    replay = merge_new_events([], history, set())
    assert [e["event_id"] for e in first] == ["1", "2", "3"]
    assert [e["event_id"] for e in replay] == ["1", "2", "3"]


@requires_appwrite
def test_stream_emits_ordered_events(client):
    from agent_arena.auth import get_current_user
    from agent_arena.main import app

    user_id = make_user_id()
    app.dependency_overrides[get_current_user] = lambda: user_id
    try:
        battle = client.post(
            "/battles",
            json={
                "format_id": _real_format_id(),
                "model_ids": ["host:openrouter-free", "host:openrouter-free"],
                "arena_size": 2,
                "timeout_seconds": 600,
                "round_visibility": "isolated",
                "save": False,
            },
        ).json()
        with client.stream("GET", f"/battles/{battle['id']}/stream") as resp:
            assert resp.status_code == 200
            text = "".join(resp.iter_text())
    finally:
        app.dependency_overrides.clear()

    assert "event: battle_status" in text
    assert "event: phase_start" in text
    assert "event: artifact" in text
    assert "event: scores" in text
    assert "event: done" in text
    assert '"status": "completed"' in text
    # phase_start must precede artifact within the stream text
    assert text.index("event: phase_start") < text.index("event: artifact")


@requires_appwrite
def test_stream_picks_up_durable_event_after_connect(client, monkeypatch):
    """A durable event written on another replica (empty local queue) still
    reaches an already-open SSE connection via the reload loop."""
    from agent_arena import battles as battles_mod
    from agent_arena import db as arena_db
    from agent_arena import event_bus
    from agent_arena.auth import get_current_user
    from agent_arena.main import app

    monkeypatch.setattr(battles_mod, "_DURABLE_RELOAD_INTERVAL", 0.1)
    # Simulate a fresh replica: local queue is empty, all events come from durable store
    monkeypatch.setattr(event_bus, "subscribe", lambda battle_id: [])

    user_id = make_user_id()
    app.dependency_overrides[get_current_user] = lambda: user_id
    try:
        databases = arena_db.get_databases()
        database_id = arena_db.get_database_id()
        battle = databases.create_document(
            database_id,
            "battles",
            "unique()",
            {
                "user_id": user_id,
                "format_id": _real_format_id(),
                "model_ids": ["host:openrouter-free", "host:openrouter-free"],
                "arena_size": 2,
                "status": "running",
                "timeout_seconds": 600,
                "round_visibility": "isolated",
                "saved": False,
            },
        )
        battle_id = battle.id

        # Written after the stream snapshot, like another replica persisting late.
        # Also flip the battle terminal so the SSE generator returns and the
        # stream closes (avoids blocking forever on a "running" battle).
        late_id = f"late-{battle_id[:12]}"

        def _write_late():
            time.sleep(1.5)
            event_bus._persist_one(
                battle_id,
                {
                    "event_id": late_id,
                    "type": "artifact",
                    "data": {
                        "phase": "p",
                        "model_id": "m",
                        "artifact": "from-other-replica",
                    },
                    "created_at": time.time(),
                },
            )
            databases.update_document(
                database_id, "battles", battle_id, {"status": "completed"}
            )

        writer = threading.Thread(target=_write_late, daemon=True)
        writer.start()
        with client.stream("GET", f"/battles/{battle_id}/stream") as resp:
            assert resp.status_code == 200
            import time as _t

            deadline = _t.time() + 20
            lines = []
            for line in resp.iter_lines():
                lines.append(line)
                if "from-other-replica" in line:
                    break
                if _t.time() > deadline:
                    break
        assert any("from-other-replica" in line for line in lines), (
            "durable event written after connect was not streamed"
        )
    finally:
        app.dependency_overrides.clear()
