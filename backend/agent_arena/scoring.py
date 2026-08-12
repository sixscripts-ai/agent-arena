"""Persist battle scores + leaderboard updates (shared by in-process + sandbox paths)."""

from __future__ import annotations

import json
from typing import Any


def parse_scores_payload(artifact: str | dict | None) -> dict[str, float] | None:
    """Extract {model_id: float} from a judge scores artifact / event payload."""
    if artifact is None:
        return None
    data: Any = artifact
    if isinstance(artifact, str):
        text = artifact.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    raw = data.get("scores")
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, float] = {}
    for mid, val in raw.items():
        try:
            out[str(mid)] = float(val)
        except (TypeError, ValueError):
            continue
    return out or None


def finalize_battle_scores(
    databases,
    database_id: str,
    battle_id: str,
    battle,
    scores: dict[str, float] | None,
    *,
    judge_model: str = "host-judge",
) -> None:
    """Write scores docs + apply Elo. Idempotent if scores already exist for battle."""
    if not scores:
        return
    from appwrite.query import Query

    from . import leaderboard

    try:
        existing = databases.list_documents(
            database_id,
            "scores",
            queries=[Query.equal("battle_id", battle_id), Query.limit(1)],
        )
        if existing.documents:
            return
    except Exception:
        pass

    battle_data = battle.data if hasattr(battle, "data") else battle
    for mid, value in scores.items():
        try:
            databases.create_document(
                database_id,
                "scores",
                "unique()",
                {
                    "battle_id": battle_id,
                    "model_id": mid,
                    "score": float(value),
                    "judge_model": judge_model,
                    "justification": "judged",
                },
            )
        except Exception:
            pass
    try:
        leaderboard.apply_result(
            databases,
            database_id,
            battle_data["format_id"],
            list(battle_data["model_ids"]),
            scores,
        )
    except Exception:
        pass
