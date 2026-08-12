"""Formats 9/10: direct exchange where each side can adapt to the opponent."""
from __future__ import annotations

from .base import Executor
from .progressive import ITERATION_RULES, call_progressive_model, clip


class DirectDuelExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        roles = participants[:2]
        transcript: list[str] = []
        latest: dict[str, str] = {}
        turns = max(1, min(8, int(format_config.get("duel_turns", 3))))

        for turn in range(turns):
            for role in roles:
                model_id = role_to_model.get(role)
                if not model_id:
                    continue

                previous = latest.get(model_id, "")
                # A direct duel is interactive by definition. Even when UI visibility is
                # isolated, the competing model must see the opponent's preceding moves or
                # it cannot counter/adapt. round_visibility still controls presentation.
                visible = "\n".join(transcript[-8:])
                messages = [
                    {
                        "role": "system",
                        "content": (
                            f"You are '{role}' in a direct duel ({format_config.get('name', '')}). "
                            f"Turn {turn + 1}/{turns}. Stay in character and actively counter the opponent.\n\n"
                            f"{ITERATION_RULES}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Transcript so far:\n{visible or '(start)'}\n\n"
                            f"Your previous move:\n{clip(previous) if previous else '(none)'}\n\n"
                            "Make the strongest next move in response to what has actually happened. "
                            "Do not repeat your opening move unless repetition itself is strategically necessary."
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
                latest[model_id] = content
                line = f"[{role}/{model_id} T{turn + 1}]: {content}"
                transcript.append(line)
                art = {
                    "phase": phase_name,
                    "model_id": model_id,
                    "artifact": content,
                    "role": role,
                    "turn": turn,
                }
                artifacts.append(art)
                client.round(battle_id, phase_name, model_id, content)

        client.round(
            battle_id,
            phase_name,
            "system",
            "\n".join(transcript),
            event_type="transcript",
        )
        return artifacts
