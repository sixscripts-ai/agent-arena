"""Format 12: thin tool sim (read/write files in a workdir)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .base import Executor


class AgentVsAgentExecutor(Executor):
    def run_phase(self, *, client, battle_id, phase, role_to_model, history, format_config, round_visibility):
        artifacts = []
        phase_name = phase["name"]
        participants = [p for p in phase.get("participants", []) if p != "judge"]
        turns = int(format_config.get("agent_turns", 3))
        with tempfile.TemporaryDirectory(prefix="arena-agent-") as tmp:
            work = Path(tmp)
            (work / "notes.txt").write_text("shared board\n", encoding="utf-8")
            log: list[str] = []
            for turn in range(turns):
                for role in participants:
                    model_id = role_to_model.get(role)
                    if not model_id:
                        continue
                    board = (work / "notes.txt").read_text(encoding="utf-8")
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                f"You are agent '{role}'. Tools: WRITE:<text> appends to notes.txt; "
                                f"READ returns notes. Goal: complete the mission in format "
                                f"'{format_config.get('name', '')}'. Reply with one action."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Turn {turn + 1}/{turns}. notes.txt:\n{board}\n\nAction:",
                        },
                    ]
                    content = client.model(battle_id, model_id, messages, phase=phase_name)
                    action_result = self._apply(work, content)
                    line = f"[{role} T{turn + 1}] {content[:500]} => {action_result}"
                    log.append(line)
                    art = {
                        "phase": phase_name,
                        "model_id": model_id,
                        "artifact": f"{content}\nRESULT: {action_result}",
                        "role": role,
                    }
                    artifacts.append(art)
                    client.round(battle_id, phase_name, model_id, art["artifact"])
            client.round(battle_id, phase_name, "system", "\n".join(log), event_type="action_log")
        return artifacts

    def _apply(self, work: Path, content: str) -> str:
        text = content.strip()
        upper = text.upper()
        if upper.startswith("WRITE:"):
            payload = text.split(":", 1)[1].strip()
            with open(work / "notes.txt", "a", encoding="utf-8") as f:
                f.write(payload + "\n")
            return "wrote"
        if upper.startswith("READ") or "READ" in upper[:20]:
            return (work / "notes.txt").read_text(encoding="utf-8")[:2000]
        # default: treat whole reply as write
        with open(work / "notes.txt", "a", encoding="utf-8") as f:
            f.write(text[:500] + "\n")
        return "appended"
