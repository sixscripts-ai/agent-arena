"""Battle loop: role map, phases (skip judge), executors, host judge."""
from __future__ import annotations

import json
import threading
import time
from typing import Callable

from .client import InternalClient
from .executors import get_executor


def playable_roles(roles: list[str]) -> list[str]:
    return [r for r in roles if r != "judge"]


def map_roles(roles: list[str], model_ids: list[str]) -> dict[str, str]:
    playable = playable_roles(roles)
    if len(playable) != len(model_ids):
        raise ValueError(f"role/model mismatch: {playable} vs {model_ids}")
    return dict(zip(playable, model_ids))


def run_battle_loop(
    *,
    battle_id: str,
    format_config: dict,
    model_ids: list[str],
    round_visibility: str = "isolated",
    timeout_seconds: int = 600,
    client: InternalClient,
    status_check: Callable[[], str] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """Drive phases until complete/failed/cancelled. Returns scores dict."""
    deadline = time.time() + timeout_seconds
    stop = threading.Event()

    def watchdog():
        remaining = max(0.0, deadline - time.time())
        if stop.wait(remaining):
            return
        if on_status:
            on_status("failed")

    wd = threading.Thread(target=watchdog, daemon=True)
    wd.start()

    try:
        if on_status:
            on_status("running")
        roles = format_config.get("roles", [])
        role_to_model = map_roles(roles, model_ids)
        engine = format_config.get("engine", "scripted")
        executor = get_executor(engine)
        phases = format_config.get("phases", [])
        history: list[dict] = []

        for phase in phases:
            if status_check and status_check() == "cancelled":
                if on_status:
                    on_status("cancelled")
                return {}
            if time.time() > deadline:
                if on_status:
                    on_status("failed")
                return {}
            # skip pure judge phases — host judge runs after real work
            participants = [p for p in phase.get("participants", []) if p != "judge"]
            if not participants:
                continue
            client.round(battle_id, phase["name"], "system", f"phase_start:{phase['name']}", event_type="phase_start")
            arts = executor.run_phase(
                client=client,
                battle_id=battle_id,
                phase=phase,
                role_to_model=role_to_model,
                history=history,
                format_config=format_config,
                round_visibility=round_visibility,
            )
            history.extend(arts)

        rubric = format_config.get("judge_rubric") or "Score each model 0-100 fairly."
        weights = format_config.get("scoring_weights")
        result = client.judge(battle_id, rubric, history, weights=weights)
        scores = result.get("scores") or {}
        client.round(
            battle_id,
            "judge",
            "system",
            json.dumps(result),
            event_type="scores",
        )
        if on_status:
            on_status("completed")
        return scores
    except Exception:
        if on_status:
            on_status("failed")
        raise
    finally:
        stop.set()
