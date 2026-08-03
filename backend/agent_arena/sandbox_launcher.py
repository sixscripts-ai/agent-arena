"""Start a battle: prefer Modal Sandbox; fall back to in-process runner."""
from __future__ import annotations

import json
import os
import threading

from . import db, event_bus
from .config import settings
from .sandbox.client import HttpTransport, InternalClient
from .sandbox.runner import run_battle_loop


def _backend_public_url() -> str:
    return os.environ.get(
        "BACKEND_PUBLIC_URL",
        "https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run",
    )


def _load_battle(battle_id: str):
    databases = db.get_databases()
    database_id = db.get_database_id()
    battle = databases.get_document(database_id, "battles", battle_id)
    format_doc = databases.get_document(database_id, "formats", battle.data["format_id"])
    cfg = json.loads(format_doc.data["config"])
    return databases, database_id, battle, cfg


def _set_status(databases, database_id: str, battle_id: str, status: str) -> None:
    try:
        databases.update_document(database_id, "battles", battle_id, {"status": status})
    except Exception:
        pass
    event_bus.publish(battle_id, {"type": "battle_status", "data": {"status": status}})


def run_in_process(battle_id: str) -> None:
    """Hermetic/local path: runner in this process using HttpTransport to self or Fake."""
    databases, database_id, battle, cfg = _load_battle(battle_id)
    key = settings().get("INTERNAL_API_KEY") or ""
    base = os.environ.get("INTERNAL_BASE_URL") or "http://127.0.0.1:8000"
    # When no server, use direct in-memory bridge via local functions
    if not key or os.environ.get("ARENA_INPROCESS_DIRECT") == "1":
        _run_direct(battle_id, databases, database_id, battle, cfg)
        return
    client = InternalClient(HttpTransport(base, key))

    def status_check() -> str:
        b = databases.get_document(database_id, "battles", battle_id)
        return b.data["status"]

    def on_status(status: str) -> None:
        _set_status(databases, database_id, battle_id, status)
        if status == "completed":
            _finalize_scores(databases, database_id, battle_id, battle, None)

    try:
        scores = run_battle_loop(
            battle_id=battle_id,
            format_config=cfg,
            model_ids=list(battle.data["model_ids"]),
            round_visibility=battle.data.get("round_visibility", "isolated"),
            timeout_seconds=int(battle.data.get("timeout_seconds") or 600),
            client=client,
            status_check=status_check,
            on_status=on_status,
        )
        if scores:
            _finalize_scores(databases, database_id, battle_id, battle, scores)
    except Exception:
        _set_status(databases, database_id, battle_id, "failed")


def _run_direct(battle_id, databases, database_id, battle, cfg) -> None:
    """Call internal handlers without HTTP (tests + local)."""
    from .sandbox.client import FakeTransport, InternalClient
    from . import judge as judge_mod
    from .providers import get_model_call_spec
    from .redact import sanitize_artifact
    from . import llm_client

    transport = FakeTransport()

    # Wire FakeTransport to real model/judge when keys exist; else canned
    def model_post(path, body):
        if path == "/internal/model":
            try:
                base, style, key, model = get_model_call_spec(
                    body["model_id"], battle.data["user_id"]
                )
                content = llm_client.chat_completion(
                    base_url=base,
                    auth_style=style,
                    api_key=key,
                    model=model,
                    messages=body.get("messages") or [],
                )
            except Exception:
                content = f"[stub:{body['model_id']}]"
            transport.rounds  # keep
            return {"content": content}
        if path == "/internal/judge":
            try:
                return judge_mod.judge_battle(
                    model_ids=list(battle.data["model_ids"]),
                    artifacts=body.get("artifacts") or [],
                    rubric=body.get("rubric") or "score",
                    weights=body.get("weights"),
                )
            except Exception:
                mids = list(battle.data["model_ids"])
                scores = {m: 50.0 + i for i, m in enumerate(mids)}
                return {
                    "scores": scores,
                    "justifications": {m: "fallback" for m in mids},
                    "judge_model": "fallback",
                }
        if path == "/internal/round":
            art = sanitize_artifact(body.get("artifact", ""))
            databases.create_document(database_id, "rounds", "unique()", {
                "battle_id": battle_id,
                "phase": body.get("phase", ""),
                "model_id": body.get("model_id", ""),
                "artifact": art,
            })
            event_bus.publish(battle_id, {
                "type": body.get("event_type", "artifact"),
                "data": {
                    "phase": body.get("phase"),
                    "model_id": body.get("model_id"),
                    "artifact": art,
                },
            })
            return {"ok": True}
        raise RuntimeError(path)

    transport.post = model_post  # type: ignore[method-assign]
    client = InternalClient(transport)

    def status_check() -> str:
        b = databases.get_document(database_id, "battles", battle_id)
        return b.data["status"]

    def on_status(status: str) -> None:
        _set_status(databases, database_id, battle_id, status)

    try:
        _set_status(databases, database_id, battle_id, "running")
        scores = run_battle_loop(
            battle_id=battle_id,
            format_config=cfg,
            model_ids=list(battle.data["model_ids"]),
            round_visibility=battle.data.get("round_visibility", "isolated"),
            timeout_seconds=int(battle.data.get("timeout_seconds") or 600),
            client=client,
            status_check=status_check,
            on_status=on_status,
        )
        if scores:
            _finalize_scores(databases, database_id, battle_id, battle, scores)
            if battle.data.get("status") != "completed":
                _set_status(databases, database_id, battle_id, "completed")
    except Exception:
        _set_status(databases, database_id, battle_id, "failed")


def _finalize_scores(databases, database_id, battle_id, battle, scores) -> None:
    if not scores:
        return
    from . import leaderboard

    for mid, value in scores.items():
        databases.create_document(database_id, "scores", "unique()", {
            "battle_id": battle_id,
            "model_id": mid,
            "score": float(value),
            "judge_model": "host-judge",
            "justification": "judged",
        })
    try:
        leaderboard.apply_result(
            databases,
            database_id,
            battle.data["format_id"],
            list(battle.data["model_ids"]),
            scores,
        )
    except Exception:
        pass


def try_spawn_modal_sandbox(battle_id: str) -> str | None:
    """Spawn Modal Sandbox running the runner. Returns sandbox_id or None."""
    try:
        import modal
    except ImportError:
        return None
    key = settings().get("INTERNAL_API_KEY") or ""
    if not key:
        return None
    try:
        app = modal.App.lookup("agent-arena-backend", create_if_missing=True)
        image = (
            modal.Image.debian_slim(python_version="3.11")
            .pip_install("httpx")
            .add_local_python_source("agent_arena")
        )
        secret = modal.Secret.from_dict({
            "INTERNAL_API_KEY": key,
            "BACKEND_PUBLIC_URL": _backend_public_url(),
        })
        sb = modal.Sandbox.create(
            "python",
            "-c",
            (
                "from agent_arena.sandbox.entrypoint import main; "
                f"main({battle_id!r})"
            ),
            image=image,
            secrets=[secret],
            timeout=int(os.environ.get("SANDBOX_TIMEOUT", "900")),
            app=app,
        )
        return getattr(sb, "object_id", None) or getattr(sb, "sandbox_id", None) or str(sb)
    except Exception:
        return None


def start_battle(battle_id: str) -> None:
    """Entry used by BackgroundTasks / Modal."""
    sandbox_id = None
    if os.environ.get("ARENA_USE_MODAL_SANDBOX") == "1":
        sandbox_id = try_spawn_modal_sandbox(battle_id)
        if sandbox_id:
            try:
                databases = db.get_databases()
                databases.update_document(
                    db.get_database_id(), "battles", battle_id, {"sandbox_id": sandbox_id}
                )
            except Exception:
                pass
            return
    # Default: in-process direct runner (works in tests without Modal)
    os.environ.setdefault("ARENA_INPROCESS_DIRECT", "1")
    run_in_process(battle_id)


def stop_sandbox(sandbox_id: str) -> None:
    if not sandbox_id:
        return
    try:
        import modal
        sb = modal.Sandbox.from_id(sandbox_id)
        sb.terminate()
    except Exception:
        pass
