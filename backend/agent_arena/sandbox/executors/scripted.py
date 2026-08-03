"""Generic phase scaffolding with real model calls (no bespoke engine logic)."""
from __future__ import annotations

from .base import Executor


class ScriptedExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        for role in participants:
            model_id = role_to_model.get(role)
            if not model_id:
                continue
            prior = "\n".join(
                f"[{a['phase']}/{a['model_id']}]: {a['artifact'][:2000]}"
                for a in history
                if round_visibility == "open" or a["model_id"] == model_id
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are role '{role}' in battle format '{format_config.get('name', '')}'. "
                        f"Phase: {phase_name}. Produce your move."
                    ),
                },
                {"role": "user", "content": f"Prior context:\n{prior or '(none)'}\n\nYour move:"},
            ]
            content = client.model(battle_id, model_id, messages, phase=phase_name)
            art = {"phase": phase_name, "model_id": model_id, "artifact": content, "role": role}
            artifacts.append(art)
            client.round(battle_id, phase_name, model_id, content)
        return artifacts
