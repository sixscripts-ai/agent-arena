"""Deep runtime health: Appwrite, internal auth, hosts, sandbox mode, events, formats."""

from __future__ import annotations

import os
import time
import uuid

from fastapi import APIRouter

from appwrite.query import Query

from . import db, event_bus
from .config import settings
from .providers import configured_host_providers
from .sandbox.executors import get_executor
from .sandbox.executors.advanced_executor import AdvancedExecutor
from .seed_formats import ALL_FORMATS

router = APIRouter(tags=["health"])


def runtime_health() -> dict:
    s = settings()
    checks: dict = {}
    errors: list[str] = []

    try:
        databases = db.get_databases()
        database_id = db.get_database_id()
        databases.list_documents(database_id, "formats", queries=[Query.limit(1)])
        checks["appwrite_read"] = True
    except Exception as exc:
        checks["appwrite_read"] = False
        errors.append(f"appwrite_read: {type(exc).__name__}")

    probe_id = f"h{uuid.uuid4().hex[:20]}"
    try:
        databases = db.get_databases()
        database_id = db.get_database_id()
        databases.create_document(
            database_id,
            "battle_events",
            probe_id,
            {
                "battle_id": probe_id,
                "event_id": probe_id,
                "payload": '{"type":"health","data":{}}',
                "created_at": time.time(),
            },
        )
        databases.get_document(database_id, "battle_events", probe_id)
        databases.delete_document(database_id, "battle_events", probe_id)
        checks["appwrite_write"] = True
        checks["event_persistence"] = True
    except Exception as exc:
        checks["appwrite_write"] = False
        checks["event_persistence"] = False
        errors.append(f"event_persistence: {type(exc).__name__}")
        try:
            db.get_databases().delete_document(
                db.get_database_id(), "battle_events", probe_id
            )
        except Exception:
            pass

    checks["internal_key_configured"] = bool(s.get("INTERNAL_API_KEY"))
    if not checks["internal_key_configured"]:
        errors.append("internal_key_configured: missing")

    hosts = configured_host_providers()
    checks["host_models"] = len(hosts)
    checks["host_model_ids"] = [p["id"] for p in hosts]
    if not hosts:
        errors.append("host_models: none configured")

    mock = os.environ.get("ARENA_USE_MOCK") == "1"
    modal = os.environ.get("ARENA_USE_MODAL_SANDBOX") == "1"
    checks["mock_mode"] = mock
    checks["modal_sandbox"] = modal
    if mock:
        errors.append("mock_mode: ARENA_USE_MOCK=1")
    if not modal:
        errors.append("modal_sandbox: ARENA_USE_MODAL_SANDBOX is not 1")

    try:
        formats = db.get_databases().list_documents(
            db.get_database_id(), "formats", queries=[Query.limit(100)]
        )
        checks["format_count"] = len(formats.documents)
    except Exception:
        checks["format_count"] = len(ALL_FORMATS)

    sample = ALL_FORMATS[0] if ALL_FORMATS else {"name": "x"}
    checks["universal_routing"] = isinstance(get_executor(sample), AdvancedExecutor)
    if not checks["universal_routing"]:
        errors.append("universal_routing: sample format is not AdvancedExecutor")

    injection = next(
        (f for f in ALL_FORMATS if f.get("name") == "Injection agent vs hardened agent"),
        None,
    )
    if injection is not None:
        checks["injection_universal"] = isinstance(get_executor(injection), AdvancedExecutor)
    checks["event_bus_ok"] = True
    event_bus.publish(probe_id, {"type": "health", "data": {"ok": True}})

    ok = not errors
    return {
        "ok": ok,
        "status": "ok" if ok else "degraded",
        "checks": checks,
        "errors": errors,
    }


@router.get("/health/runtime")
def health_runtime():
    return runtime_health()
