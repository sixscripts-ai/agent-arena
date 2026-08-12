"""Shared helpers that make repeated battle turns genuinely progressive."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable

MAX_CONTEXT_CHARS = 6000
MAX_ARTIFACT_CHARS = 3000

ITERATION_RULES = """You are competing in a progressive multi-turn battle.
Treat the latest prior artifact as the current working state, not as a prompt to restart.
On every turn after the first, make a material improvement or counter-move.
Preserve parts that already work. Fix the highest-impact weakness first.
When opponent context is available, identify what it does better and respond to that advantage.
Do not repeat your opening answer, merely paraphrase it, or spend the turn describing changes you did not make.
Return the improved artifact or move itself, not a plan for a future turn."""


def clip(text: str | None, limit: int = MAX_ARTIFACT_CHARS) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def latest_for_model(history: list[dict[str, Any]], model_id: str) -> str:
    for item in reversed(history):
        if item.get("model_id") == model_id:
            return str(item.get("artifact") or "")
    return ""


def latest_for_other(history: list[dict[str, Any]], model_id: str) -> str:
    for item in reversed(history):
        other = item.get("model_id")
        if other and other not in (model_id, "system"):
            return str(item.get("artifact") or "")
    return ""


def build_phase_context(
    history: list[dict[str, Any]],
    *,
    model_id: str,
    input_phases: Iterable[str] = (),
    round_visibility: str = "isolated",
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """Return compact context without breaking declared phase dependencies.

    Own history is always visible. In open mode all participant history is visible.
    In isolated mode, opponent artifacts remain hidden unless the current phase
    explicitly declares their phase as an input. That keeps anti-cheat behavior
    while still allowing formats such as attack -> defend -> adapt to function.
    """
    allowed_inputs = set(input_phases)
    selected: list[dict[str, Any]] = []
    for item in history:
        item_model = item.get("model_id")
        item_phase = str(item.get("phase") or "")
        if (
            item_model == model_id
            or round_visibility == "open"
            or item_phase in allowed_inputs
        ):
            selected.append(item)

    # Recent state is normally more useful than replaying the full session.
    selected = selected[-8:]
    parts: list[str] = []
    for item in selected:
        artifact = clip(str(item.get("artifact") or ""))
        if not artifact:
            continue
        parts.append(
            f"[{item.get('phase', '?')}/{item.get('model_id', '?')}]:\n{artifact}"
        )

    text = "\n\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def is_stagnant(previous: str | None, current: str | None, threshold: float = 0.985) -> bool:
    """Detect an unchanged or near-copy submission without rewarding noisy rewrites."""
    prev = _normalize(previous)
    cur = _normalize(current)
    if not prev or not cur:
        return False
    if prev == cur:
        return True
    # Short moves can legitimately be terse; only exact duplicates are blocked.
    if min(len(prev), len(cur)) < 120:
        return False
    # Bound comparison cost for large code artifacts.
    prev = prev[:8000]
    cur = cur[:8000]
    return SequenceMatcher(None, prev, cur, autojunk=False).ratio() >= threshold


def call_progressive_model(
    *,
    client,
    battle_id: str,
    model_id: str,
    messages: list[dict],
    phase: str,
    previous_artifact: str | None = None,
) -> str:
    """Call a competitor and retry once only when it effectively repeats itself."""
    content = client.model(battle_id, model_id, messages, phase=phase)
    if not previous_artifact or not is_stagnant(previous_artifact, content):
        return content

    retry_messages = [
        *messages,
        {"role": "assistant", "content": clip(content, 4000)},
        {
            "role": "user",
            "content": (
                "Your draft is effectively unchanged from your previous turn. "
                "Do not restart or paraphrase it. Make at least one substantive, "
                "score-relevant change that addresses the current context or opponent, "
                "then return the complete replacement artifact/move only."
            ),
        },
    ]
    return client.model(battle_id, model_id, retry_messages, phase=phase)


def _normalize(text: str | None) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value
