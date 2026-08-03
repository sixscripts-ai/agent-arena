"""Format 20: Time-limited siege.

Both players brute-force a multi-layer vault under a per-layer time budget.
Outcomes: LAYERS_BREACHED_<n> per player.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from ..base import Executor
from .._harness import model_code, read_outcome, run_python, write_assets

NAME = "Time-limited siege"
SLUG = "time-limited-siege"

SIEGE_HARNESS = """\
import hashlib, subprocess, sys
BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 20
LAYERS = int(sys.argv[2]) if len(sys.argv) > 2 else 2

def crack(script):
    breached = 0
    for i in range(LAYERS):
        h = open("layers/layer%d.hash" % i).read().strip()
        try:
            proc = subprocess.run(["python3", script, str(i)], capture_output=True, text=True, timeout=BUDGET)
        except subprocess.TimeoutExpired:
            break
        guess = [l for l in proc.stdout.splitlines() if l.strip()]
        if guess and hashlib.sha256(guess[-1].strip().encode()).hexdigest() == h:
            breached += 1
        else:
            break
    return breached

a = crack("attack_a.py")
b = crack("attack_b.py")
print("OUTCOME: LAYERS_BREACHED_" + str(max(a, b)))
print("A=%d B=%d" % (a, b))
"""

ATTACK_TEMPLATE = """\
import hashlib, itertools, string, sys
layer = int(sys.argv[1])
target = open("layers/layer%d.hash" % layer).read().strip()
for combo in itertools.product(string.ascii_lowercase, repeat=4):
    pw = "".join(combo)
    if hashlib.sha256(pw.encode()).hexdigest() == target:
        print(pw)
        break
"""


class TimeLimitedSiegeExecutor(Executor):
    def run_battle(
        self,
        *,
        battle_id,
        format_config,
        model_ids,
        round_visibility,
        timeout_seconds,
        role_to_model,
        client,
        status_check=None,
        on_status=None,
        deadline=None,
        stop=None,
    ):
        pa = role_to_model.get("player_a")
        pb = role_to_model.get("player_b")
        exec_timeout = int(format_config.get("exec_timeout_seconds", 180))
        layers = format_config.get("layers", [])
        budget = int(format_config.get("layer_budget_s", 20))
        markers = format_config.get("outcome_markers", [])
        history: list[dict] = []
        with tempfile.TemporaryDirectory(prefix="arena-fmt20-") as tmp:
            work = Path(tmp)
            write_assets(work, {"siege.py": SIEGE_HARNESS})
            for i, pw in enumerate(layers):
                write_assets(
                    work,
                    {f"layers/layer{i}.hash": hashlib.sha256(pw.encode()).hexdigest()},
                )
            for role, script, mid in (
                ("player_a", "attack_a.py", pa),
                ("player_b", "attack_b.py", pb),
            ):
                if mid:
                    code = model_code(
                        client,
                        battle_id,
                        mid,
                        "phase1",
                        [
                            {
                                "role": "system",
                                "content": (
                                    f"You are {role} in a time-limited siege. Write {script} that takes a layer "
                                    "index in sys.argv[1], reads layers/layer<idx>.hash, brute-forces the 4-char "
                                    "lowercase password, and prints it. Output ONLY code."
                                ),
                            },
                            {"role": "user", "content": "Emit the cracker."},
                        ],
                    )
                    if not code:
                        code = ATTACK_TEMPLATE
                    write_assets(work, {script: code})
                    history.append(
                        {
                            "phase": "phase1",
                            "model_id": mid,
                            "artifact": code,
                            "role": role,
                        }
                    )
                    client.round(battle_id, "phase1", mid, code)
            out, err, rc = run_python(
                work / "siege.py",
                cwd=work,
                timeout=exec_timeout,
                args=[str(budget), str(len(layers))],
            )
            a = b = 0
            for line in out.splitlines():
                if line.startswith("A="):
                    try:
                        a = int(line.split("A=")[1].split()[0])
                        b = int(line.split("B=")[1])
                    except Exception:
                        pass
            result = {
                "player_a": self.guard(f"LAYERS_BREACHED_{a}", markers),
                "player_b": self.guard(f"LAYERS_BREACHED_{b}", markers),
                "total_layers": len(layers),
            }
            line = self.emit_result(client, battle_id, "judge", result)
            history[-1]["artifact"] = history[-1]["artifact"] + "\n" + line
            history.append(
                {
                    "phase": "judge",
                    "model_id": "system",
                    "artifact": f"---HARNESS---\n{out}\n{err}\nrc={rc}\n{line}",
                }
            )
        return self.finish(
            client=client,
            battle_id=battle_id,
            format_config=format_config,
            history=history,
            on_status=on_status,
        )
