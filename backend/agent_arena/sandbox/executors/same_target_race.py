"""Formats 6/7: both models get the same target; collect independent answers."""
from __future__ import annotations

from .base import Executor

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
        # isolated: don't show opponent answers until judging
        for role in participants:
            model_id = role_to_model.get(role)
            if not model_id:
                continue
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are '{role}' in a same-target race ({format_config.get('name', '')}). "
                        "Solve/fix/review the target. Return your full answer."
                    ),
                },
                {"role": "user", "content": f"TARGET:\n```\n{target}\n```\n\nYour solution:"},
            ]
            content = client.model(battle_id, model_id, messages, phase=phase_name)
            # lightweight "test" signal for debugging race
            passed = "assert" in content.lower() or "fix" in content.lower() or "bug" in content.lower()
            result = f"{content}\n\n---\nexecutor_check: {'likely_ok' if passed else 'unclear'}"
            art = {"phase": phase_name, "model_id": model_id, "artifact": result, "role": role}
            artifacts.append(art)
            if round_visibility == "open":
                client.round(battle_id, phase_name, model_id, result)
            else:
                # still stream to backend (persisted); UI can gate isolated display
                client.round(battle_id, phase_name, model_id, result)
        return artifacts
