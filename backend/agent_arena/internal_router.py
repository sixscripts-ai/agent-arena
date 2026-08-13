"""Sandbox → backend callbacks. Hidden from OpenAPI; auth via X-Internal-Key."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from threading import Lock

from appwrite.exception import AppwriteException
from appwrite.query import Query
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from . import db, event_bus, judge, llm_client
from .config import settings
from .providers import get_model_call_spec
from .redact import sanitize_artifact

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


def _active_battle(databases, database_id: str, battle_id: str):
    try:
        battle = databases.get_document(database_id, "battles", battle_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Battle not found") from exc
    if battle.data.get("status") not in ("queued", "running"):
        raise HTTPException(status_code=409, detail="battle not active")
    return battle


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
    sequence: int | None = None


class StatusBody(BaseModel):
    battle_id: str


class FinalizeBody(BaseModel):
    battle_id: str
    status: str = "completed"
    scores: dict[str, float] = Field(default_factory=dict)


def _finalize_scores(databases, database_id: str, battle_id: str, scores: dict) -> bool:
    """Persist score docs + Elo for a finished battle. Idempotent per battle."""
    existing = databases.list_documents(
        database_id,
        "scores",
        queries=[Query.equal("battle_id", battle_id), Query.limit(1)],
    )
    if existing.documents:
        return False
    for mid, value in scores.items():
        databases.create_document(
            database_id,
            "scores",
            "unique()",
            {
                "battle_id": battle_id,
                "model_id": mid,
                "score": float(value),
                "judge_model": "host-judge",
                "justification": "judged",
            },
        )
    return True


@router.post("/finalize")
def internal_finalize(body: FinalizeBody, _ok: bool = Depends(require_internal_key)):
    """Sandbox reports final outcome: persist scores, update battle status, apply Elo."""
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
    try:
        battle = databases.get_document(database_id, "battles", body.battle_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Battle not found") from exc
    if battle.data.get("status") not in ("queued", "running"):
        raise HTTPException(status_code=409, detail="battle not active")
    status = body.status if body.status in ("completed", "failed") else "completed"
    if status == "completed" and body.scores:
        try:
            if _finalize_scores(databases, database_id, body.battle_id, body.scores):
                from . import leaderboard

                leaderboard.apply_result(
                    databases,
                    database_id,
                    battle.data["format_id"],
                    list(battle.data.get("model_ids", [])),
                    body.scores,
                )
        except Exception:
            pass
    databases.update_document(
        database_id, "battles", body.battle_id, {"status": status}
    )
    if status == "completed" and body.scores:
        event_bus.publish(
            body.battle_id, {"type": "scores", "data": {"scores": body.scores}}
        )
    event_bus.publish(
        body.battle_id,
        {
            "type": "battle_status",
            "data": {"status": status},
        },
    )
    return {"ok": True, "status": status}


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


@router.post("/round")
def internal_round(body: RoundBody, _ok: bool = Depends(require_internal_key)):
    _rate_limit(body.battle_id)
    databases = db.get_databases()
    database_id = db.get_database_id()
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
    event_id = f"{body.battle_id}:{body.sequence if body.sequence is not None else int(time.time() * 1000)}"
    event = {
        "type": body.event_type,
        "event_id": event_id,
        "sequence": body.sequence,
        "data": {
            "phase": body.phase,
            "model_id": body.model_id,
            "artifact": artifact,
            "sequence": body.sequence,
        },
    }
    event_bus.publish(body.battle_id, event)
    return {"ok": True, "event_id": event_id, "sequence": body.sequence}


@router.post("/status")
def internal_status(body: StatusBody, _ok: bool = Depends(require_internal_key)):
    databases = db.get_databases()
    database_id = db.get_database_id()
    try:
        battle = databases.get_document(database_id, "battles", body.battle_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Battle not found") from exc
    return {"status": battle.data.get("status") or "unknown"}


@router.post("/reap")
def internal_reap(_ok: bool = Depends(require_internal_key)):
    from . import reaper

    reaped = reaper.reap_stale_battles()
    return {"reaped": reaped, "count": len(reaped)}
