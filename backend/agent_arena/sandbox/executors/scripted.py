"""Generic phase scaffolding with progressive state and declared-input visibility."""
from __future__ import annotations

from .base import Executor
from .progressive import (
    ITERATION_RULES,
    build_phase_context,
    call_progressive_model,
    latest_for_model,
)


class ScriptedExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        input_phases = phase.get("inputs", [])

        for role in participants:
            model_id = role_to_model.get(role)
            if not model_id:
                continue

            previous = latest_for_model(history, model_id)
            prior = build_phase_context(
                history,
                model_id=model_id,
                input_phases=input_phases,
                round_visibility=round_visibility,
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are role '{role}' in battle format '{format_config.get('name', '')}'. "
                        f"Phase: {phase_name}. Produce your move.\n\n{ITERATION_RULES}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Declared phase inputs: {input_phases or '(none)'}\n"
                        f"Relevant prior state:\n{prior or '(none)'}\n\n"
                        "Produce the strongest current move. If you have a prior artifact, improve it rather than restarting."
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
            art = {"phase": phase_name, "model_id": model_id, "artifact": content, "role": role}
            artifacts.append(art)
            client.round(battle_id, phase_name, model_id, content)
        return artifacts
