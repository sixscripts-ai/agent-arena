"""Reap battles stuck in queued/running past their timeout.

Run periodically via the Modal scheduled function (modal_entry.py) or on
demand through POST /internal/reap. Idempotent: only terminal-stale battles
are touched, and each reaped battle is failed exactly once.
"""

from __future__ import annotations

import os
import time

from appwrite.query import Query


def _started_at(battle: dict) -> float:
    for key in ("started_at", "created_at", "$createdAt"):
        value = battle.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def reap_stale_battles(databases=None, database_id: str | None = None) -> list[str]:
    from . import db, event_bus

    databases = databases or db.get_databases()
    database_id = database_id or db.get_database_id()
    now = time.time()
    grace = float(os.environ.get("REAPER_GRACE_SECONDS", "300"))
    res = databases.list_documents(
        database_id,
        "battles",
        queries=[
            Query.equal("status", ["queued", "running"]),
            Query.limit(100),
        ],
    )
    reaped: list[str] = []
    for doc in res.documents:
        battle = doc.data
        started = _started_at(battle)
        if not started:
            continue
        timeout = int(battle.get("timeout_seconds") or 600)
        age = now - started
        if age <= timeout + grace:
            continue
        reason = f"Stuck in '{battle.get('status')}' for {int(age)}s (timeout {timeout}s + grace {int(grace)}s)"
        try:
            databases.update_document(
                database_id,
                "battles",
                doc.id,
                {"status": "failed", "failure_reason": reason},
            )
        except Exception:
            continue
        sandbox_id = battle.get("sandbox_id")
        if sandbox_id:
            try:
                from . import sandbox_launcher

                sandbox_launcher.stop_sandbox(sandbox_id)
            except Exception:
                pass
        event_bus.publish(doc.id, {"type": "error", "data": {"message": reason}})
        event_bus.publish(
            doc.id,
            {"type": "battle_status", "data": {"status": "failed", "reason": reason}},
        )
        reaped.append(doc.id)
    return reaped
