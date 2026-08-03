import json

from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors.formats.time_limited_siege import (
    TimeLimitedSiegeExecutor,
)

GOOD_ATTACK = (
    "import hashlib, itertools, string, sys\n"
    "layer = int(sys.argv[1])\n"
    "target = open(f'layers/layer{layer}.hash').read().strip()\n"
    "for combo in itertools.product(string.ascii_lowercase, repeat=4):\n"
    "    pw = ''.join(combo)\n"
    "    if hashlib.sha256(pw.encode()).hexdigest() == target:\n"
    "        print(pw)\n"
    "        break\n"
)

CFG = {
    "name": "Time-limited siege",
    "engine": "high_complexity",
    "roles": ["player_a", "player_b", "judge"],
    "judge_rubric": "r",
    "scoring_weights": {"phase1": 1.0},
    "exec_timeout_seconds": 120,
    "layers": ["abcd", "bcde"],
    "layer_budget_s": 20,
    "outcome_markers": ["LAYERS_BREACHED_", "LAYERS_DEFENDED_"],
}


def test_fmt20_both_players_breach_all_layers():
    transport = FakeTransport()
    transport.model_replies = {"m-a": GOOD_ATTACK, "m-b": GOOD_ATTACK}
    transport.judge_result = {
        "scores": {"m-a": 50.0, "m-b": 50.0},
        "justifications": {},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    TimeLimitedSiegeExecutor().run_battle(
        battle_id="b",
        format_config=CFG,
        model_ids=["m-a", "m-b"],
        round_visibility="isolated",
        timeout_seconds=120,
        role_to_model={"player_a": "m-a", "player_b": "m-b"},
        client=client,
    )
    events = [r for r in transport.rounds if r.get("event_type") == "result"]
    result = json.loads(events[0]["artifact"].split(":", 1)[1])
    assert result["player_a"] == "LAYERS_BREACHED_2"
    assert result["player_b"] == "LAYERS_BREACHED_2"


def test_fmt20_smoke_siege_harness():
    from pathlib import Path
    import tempfile
    import hashlib
    from agent_arena.sandbox.executors.formats.time_limited_siege import SIEGE_HARNESS
    from agent_arena.sandbox.executors._harness import run_python, write_assets

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        layers = {
            "layers/layer0.hash": hashlib.sha256(b"abcd").hexdigest(),
            "layers/layer1.hash": hashlib.sha256(b"bcde").hexdigest(),
        }
        write_assets(
            work, {"siege.py": SIEGE_HARNESS, "attack_a.py": GOOD_ATTACK, **layers}
        )
        out, err, rc = run_python(work / "siege.py", cwd=work, timeout=120)
    assert rc == 0
    assert "OUTCOME: LAYERS_BREACHED_2" in out
