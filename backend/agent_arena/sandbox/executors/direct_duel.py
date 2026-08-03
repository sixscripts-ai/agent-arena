"""Formats 9/10: attacker vs defender turn exchange."""
from __future__ import annotations

from .base import Executor


class DirectDuelExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        # Prefer attacker/defender naming; else first two roles
        roles = participants[:2]
        transcript: list[str] = []
        turns = int(format_config.get("duel_turns", 3))
        for turn in range(turns):
            for role in roles:
                model_id = role_to_model.get(role)
                if not model_id:
                    continue
                visible = "\n".join(transcript) if round_visibility == "open" else "\n".join(
                    line for line in transcript if f"[{role}]" in line
                )
                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"You are '{role}' in a direct duel ({format_config.get('name', '')}). "
                            f"Turn {turn + 1}/{turns}. Stay in character."
                        ),
                    },
                    {"role": "user", "content": f"Transcript so far:\n{visible or '(start)'}\n\nYour move:"},
                ]
                content = client.model(battle_id, model_id, messages, phase=phase_name)
                line = f"[{role}/{model_id} T{turn + 1}]: {content}"
                transcript.append(line)
                art = {"phase": phase_name, "model_id": model_id, "artifact": content, "role": role, "turn": turn}
                artifacts.append(art)
                client.round(battle_id, phase_name, model_id, content)
        # full transcript as system artifact
        client.round(battle_id, phase_name, "system", "\n".join(transcript), event_type="transcript")
        return artifacts
