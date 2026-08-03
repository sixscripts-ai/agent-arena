import threading
import time
import uuid
from collections import defaultdict, deque

_queues: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def publish(battle_id: str, event: dict) -> dict:
    """Publish event locally (and optionally durable). Returns enriched event."""
    enriched = {
        **event,
        "event_id": event.get("event_id") or str(uuid.uuid4()),
        "created_at": event.get("created_at") or time.time(),
        "ts": time.time(),
    }
    with _lock:
        _queues[battle_id].append(enriched)
    _persist_async(battle_id, enriched)
    return enriched


def subscribe(battle_id: str) -> list[dict]:
    with _lock:
        return list(_queues[battle_id])


def _persist_async(battle_id: str, event: dict) -> None:
    """Best-effort durable write to Appwrite battle_events. Never raises."""
    try:
        from . import db
        import json

        databases = db.get_databases()
        database_id = db.get_database_id()
        databases.create_document(database_id, "battle_events", "unique()", {
            "battle_id": battle_id,
            "event_id": event["event_id"],
            "payload": json.dumps({"type": event.get("type"), "data": event.get("data")}),
            "created_at": float(event["created_at"]),
        })
    except Exception:
        pass


def load_durable(battle_id: str) -> list[dict]:
    """Load durable events for a battle (uuid + created_at)."""
    try:
        from appwrite.query import Query
        from . import db
        import json

        databases = db.get_databases()
        res = databases.list_documents(
            db.get_database_id(),
            "battle_events",
            queries=[Query.equal("battle_id", battle_id), Query.limit(500)],
        )
        out = []
        for d in res.documents:
            try:
                payload = json.loads(d.data["payload"])
            except Exception:
                payload = {"type": "unknown", "data": {}}
            out.append({
                "type": payload.get("type", "unknown"),
                "data": payload.get("data", {}),
                "event_id": d.data["event_id"],
                "created_at": float(d.data.get("created_at") or 0),
            })
        out.sort(key=lambda e: (e.get("created_at", 0), e.get("event_id", "")))
        return out
    except Exception:
        return []
