import json
import logging
import queue
import re
import threading
import time
import uuid
from collections import defaultdict, deque

logger = logging.getLogger("agent_arena.event_bus")

_queues: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()

_persist_queue: queue.Queue = queue.Queue()
_persist_thread: threading.Thread | None = None

_sleep = time.sleep
_DOC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$")


class DurableReadError(Exception):
    """Raised when the durable event store cannot be read."""


def _document_id(event_id: str) -> str:
    if event_id and _DOC_ID_RE.match(event_id):
        return event_id
    return str(uuid.uuid4())


def _is_duplicate_persist(exc: Exception) -> bool:
    from appwrite.exception import AppwriteException

    if isinstance(exc, AppwriteException):
        if int(getattr(exc, "code", 0) or 0) == 409:
            return True
        typ = str(getattr(exc, "type", "") or "").lower()
        if "already_exists" in typ:
            return True
    msg = str(exc).lower()
    return "already exists" in msg or "document_already_exists" in msg or "conflict" in msg


def _persist_one(battle_id: str, event: dict) -> None:
    """Persist one event durably with retries. Duplicate document id is success."""
    payload = json.dumps({"type": event.get("type"), "data": event.get("data")})
    doc_id = _document_id(str(event["event_id"]))
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            from . import db

            databases = db.get_databases()
            database_id = db.get_database_id()
            databases.create_document(
                database_id,
                "battle_events",
                doc_id,
                {
                    "battle_id": battle_id,
                    "event_id": event["event_id"],
                    "payload": payload,
                    "created_at": float(event["created_at"]),
                },
            )
            return
        except Exception as exc:
            if _is_duplicate_persist(exc):
                return
            last_exc = exc
            if attempt < 3:
                _sleep(0.25 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def _persist_or_log(battle_id: str, event: dict) -> None:
    try:
        _persist_one(battle_id, event)
    except Exception as exc:
        logger.error(
            "durable event persist failed for battle %s (event %s): %s",
            battle_id,
            event.get("event_id"),
            exc,
        )


def _persist_worker() -> None:
    while True:
        battle_id, event = _persist_queue.get()
        _persist_or_log(battle_id, event)


def _ensure_persist_thread() -> None:
    global _persist_thread
    if _persist_thread is None or not _persist_thread.is_alive():
        _persist_thread = threading.Thread(target=_persist_worker, daemon=True)
        _persist_thread.start()


def publish(battle_id: str, event: dict) -> dict:
    """Publish event locally (and optionally durable). Returns enriched event."""
    raw_id = event.get("event_id")
    event_id = (
        str(raw_id) if raw_id and _DOC_ID_RE.match(str(raw_id)) else str(uuid.uuid4())
    )
    enriched = {
        **event,
        "event_id": event_id,
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
    """Enqueue a durable Appwrite write on a background thread. Never blocks or raises."""
    _ensure_persist_thread()
    _persist_queue.put((battle_id, event))


def _decode_document(d) -> dict:
    data = getattr(d, "data", None) or d
    try:
        payload = json.loads(data["payload"])
    except Exception:
        payload = {"type": "unknown", "data": {}}
    return {
        "type": payload.get("type", "unknown"),
        "data": payload.get("data", {}),
        "event_id": data.get("event_id") or getattr(d, "id", ""),
        "created_at": float(data.get("created_at") or 0),
    }


def load_durable(
    battle_id: str,
    *,
    after_created_at: float | None = None,
    after_event_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Load durable events for a battle. Raises DurableReadError on store failure."""
    try:
        from appwrite.query import Query

        from . import db

        databases = db.get_databases()
        queries = [Query.equal("battle_id", battle_id)]
        if after_created_at is not None:
            queries.append(Query.greater_than_equal("created_at", float(after_created_at)))
        queries.append(Query.order_asc("created_at"))
        queries.append(Query.limit(int(limit)))
        res = databases.list_documents(
            db.get_database_id(),
            "battle_events",
            queries=queries,
        )
        out = [_decode_document(d) for d in res.documents]
        if after_created_at is not None:
            filtered = []
            for ev in out:
                ts = float(ev.get("created_at") or 0)
                eid = ev.get("event_id") or ""
                if ts < after_created_at:
                    continue
                if ts == after_created_at and after_event_id and eid <= after_event_id:
                    continue
                filtered.append(ev)
            out = filtered
        out.sort(key=lambda e: (e.get("created_at", 0), e.get("event_id", "")))
        return out
    except DurableReadError:
        raise
    except Exception as exc:
        raise DurableReadError(str(exc)) from exc
