"""Formats 6/7: iterative same-target race with progressive refinement."""
from __future__ import annotations

from .base import Executor
from .progressive import (
    ITERATION_RULES,
    call_progressive_model,
    clip,
    latest_for_model,
)

DEFAULT_TARGET = """# buggy.py
def add(a, b):
    return a - b  # bug: should add

def test_add():
    assert add(2, 3) == 5
"""


class SameTargetRaceExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        target = format_config.get("target_code") or DEFAULT_TARGET
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        turns = max(1, min(6, int(format_config.get("race_turns", 3))))
        current: dict[str, str] = {}

        # Seed with any earlier artifact from this model so repeated phases continue
        # from the latest state instead of reconstructing the original answer.
        for role in participants:
            model_id = role_to_model.get(role)
            if model_id:
                current[model_id] = latest_for_model(history, model_id)

        for turn in range(turns):
            for role in participants:
                model_id = role_to_model.get(role)
                if not model_id:
                    continue
                previous = current.get(model_id, "")

                opponent_context = ""
                if round_visibility == "open":
                    opponent_parts = [
                        f"[{mid} latest]:\n{clip(artifact)}"
                        for mid, artifact in current.items()
                        if mid != model_id and artifact
                    ]
                    opponent_context = "\n\n".join(opponent_parts)

                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"You are '{role}' in a same-target race ({format_config.get('name', '')}). "
                            f"Iteration {turn + 1}/{turns}. Solve/fix/review the target and return the full current answer.\n\n"
                            f"{ITERATION_RULES}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"TARGET:\n```\n{target}\n```\n\n"
                            f"YOUR PREVIOUS ARTIFACT:\n{clip(previous) if previous else '(none — establish a strong baseline)'}\n\n"
                            f"OPPONENT LATEST ARTIFACT:\n{opponent_context or '(hidden in isolated mode)'}\n\n"
                            "Return the improved complete solution. On iterations after the first, materially improve the prior artifact; do not restart from the original script."
                        ),
                    },
                ]
                content = call_progressive_model(
                    client=client,
                    battle_id=battle_id,
                    model_id=model_id,
                    messages=messages,
                    phase=phase_name,
                    previous_artifact=previous,
                )
                current[model_id] = content

                passed = "assert" in content.lower() or "fix" in content.lower() or "bug" in content.lower()
                result = (
                    f"{content}\n\n---\n"
                    f"iteration: {turn + 1}/{turns}\n"
                    f"executor_check: {'likely_ok' if passed else 'unclear'}"
                )
                art = {
                    "phase": phase_name,
                    "model_id": model_id,
                    "artifact": result,
                    "role": role,
                    "turn": turn,
                }
                artifacts.append(art)
                client.round(battle_id, phase_name, model_id, result)
        return artifacts
