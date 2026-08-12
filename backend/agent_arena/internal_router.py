"""Sandbox → backend callbacks. Hidden from OpenAPI; auth via X-Internal-Key."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from threading import Lock

from appwrite.exception import AppwriteException
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from . import db, event_bus, judge, llm_client
from .config import settings
from .providers import get_model_call_spec
from .redact import sanitize_artifact
from .scoring import finalize_battle_scores, parse_scores_payload

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

_rate_lock = Lock()
_rate_counts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 120  # calls per battle per minute


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> bool:
    import hmac

    expected = settings().get("INTERNAL_API_KEY") or ""
    if not expected:
        raise HTTPException(status_code=401, detail="internal key not configured")
    if not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=401, detail="invalid internal key")
    return True


def _rate_limit(battle_id: str) -> None:
    now = time.time()
    with _rate_lock:
        window = [t for t in _rate_counts[battle_id] if now - t < 60]
        # cleanup old battles to prevent memory leak
        if len(_rate_counts) > 1000:
            for bid in list(_rate_counts.keys()):
                if bid != battle_id and not _rate_counts[bid]:
                    del _rate_counts[bid]
        if len(window) >= _RATE_LIMIT:
            raise HTTPException(status_code=429, detail="internal rate limit exceeded")
        window.append(now)
        _rate_counts[battle_id] = window


def _get_battle(databases, database_id: str, battle_id: str):
    try:
        return databases.get_document(database_id, "battles", battle_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Battle not found") from exc


def _active_battle(databases, database_id: str, battle_id: str):
    battle = _get_battle(databases, database_id, battle_id)
    if battle.data.get("status") not in ("queued", "running"):
        raise HTTPException(status_code=409, detail="battle not active")
    return battle


def _apply_battle_status(
    databases, database_id: str, battle_id: str, battle, status: str
) -> str | None:
    """Idempotent status transition. Returns applied status or None if ignored."""
    st = (status or "").strip().lower()
    if st not in ("running", "completed", "failed", "cancelled"):
        return None
    cur = (battle.data.get("status") or "").lower()
    if st == "running":
        if cur not in ("queued", "running"):
            return None
    elif cur not in ("queued", "running", st):
        # Don't regress terminal states (e.g. completed -> failed from late watchdog).
        return None
    if cur != st:
        try:
            databases.update_document(
                database_id, "battles", battle_id, {"status": st}
            )
        except Exception:
            return None
    return st


class ModelBody(BaseModel):
    battle_id: str
    model_id: str
    phase: str = ""
    messages: list[dict] = Field(default_factory=list)
    max_tokens: int = 1024


class JudgeBody(BaseModel):
    battle_id: str
    rubric: str
    weights: dict[str, float] | None = None
    artifacts: list[dict] = Field(default_factory=list)
    judge_model: str | None = None


class RoundBody(BaseModel):
    battle_id: str
    phase: str
    model_id: str
    artifact: str
    event_type: str = "artifact"


class StatusBody(BaseModel):
    battle_id: str


@router.post("/model")
def internal_model(body: ModelBody, _ok: bool = Depends(require_internal_key)):
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
    battle = _active_battle(databases, database_id, body.battle_id)
    if body.model_id not in battle.data.get("model_ids", []):
        raise HTTPException(status_code=400, detail="model not in battle")
    base, style, key, model = get_model_call_spec(body.model_id, battle.data["user_id"])
    content = llm_client.chat_completion(
        base_url=base,
        auth_style=style,
        api_key=key,
        model=model,
        messages=body.messages,
        max_tokens=body.max_tokens,
    )
    return {"content": content}


@router.post("/judge")
def internal_judge(body: JudgeBody, _ok: bool = Depends(require_internal_key)):
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
    battle = _active_battle(databases, database_id, body.battle_id)
    model_ids = list(battle.data.get("model_ids", []))
    call_spec = None
    jpid = battle.data.get("judge_provider_id")
    if jpid:
        try:
            call_spec = get_model_call_spec(jpid, battle.data["user_id"])
        except HTTPException:
            call_spec = None  # fall back to host Kimi-K3
    result = judge.judge_battle(
        model_ids=model_ids,
        artifacts=body.artifacts,
        rubric=body.rubric,
        weights=body.weights,
        judge_model=body.judge_model,
        call_spec=call_spec,
    )
    return result


@router.post("/status")
def internal_status(body: StatusBody, _ok: bool = Depends(require_internal_key)):
    """Sandbox cancel/watchdog poll — allowed for any battle state."""
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
    battle = _get_battle(databases, database_id, body.battle_id)
    return {"status": battle.data.get("status", "unknown")}


@router.post("/round")
def internal_round(body: RoundBody, _ok: bool = Depends(require_internal_key)):
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
    # Terminal status updates must work even if a late retry races past completed.
    if body.event_type == "battle_status":
        battle = _get_battle(databases, database_id, body.battle_id)
        artifact = sanitize_artifact(body.artifact)
        applied = _apply_battle_status(
            databases, database_id, body.battle_id, battle, artifact
        )
        event_data: dict = {
            "phase": body.phase,
            "model_id": body.model_id,
            "artifact": artifact,
        }
        if applied:
            event_data["status"] = applied
        event = {"type": body.event_type, "data": event_data}
        event_bus.publish(body.battle_id, event)
        return {"ok": True, "event_id": event.get("event_id"), "status": applied}

    battle = _active_battle(databases, database_id, body.battle_id)
    if (
        body.model_id not in battle.data.get("model_ids", [])
        and body.model_id != "system"
    ):
        raise HTTPException(status_code=400, detail="model not in battle")
    artifact = sanitize_artifact(body.artifact)
    databases.create_document(
        database_id,
        "rounds",
        "unique()",
        {
            "battle_id": body.battle_id,
            "phase": body.phase,
            "model_id": body.model_id,
            "artifact": artifact,
        },
    )
    event_data = {
        "phase": body.phase,
        "model_id": body.model_id,
        "artifact": artifact,
    }
    # Sandbox path: scores event arrives before battle_status:completed (base.Executor.finish).
    if body.event_type == "scores":
        scores = parse_scores_payload(artifact)
        if scores:
            try:
                parsed = json.loads(artifact) if isinstance(artifact, str) else {}
                judge_model = (
                    str(parsed.get("judge_model") or "host-judge")
                    if isinstance(parsed, dict)
                    else "host-judge"
                )
            except Exception:
                judge_model = "host-judge"
            finalize_battle_scores(
                databases,
                database_id,
                body.battle_id,
                battle,
                scores,
                judge_model=judge_model,
            )
            event_data["scores"] = scores
    event = {
        "type": body.event_type,
        "data": event_data,
    }
    event_bus.publish(body.battle_id, event)
    return {"ok": True, "event_id": event.get("event_id")}
