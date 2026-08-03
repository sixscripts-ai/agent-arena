import json

from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors.formats.same_defense_adaptive import (
    SameDefenseAdaptiveExecutor,
)

WIN_SUBMIT = "import sys\nprint('GET /etc/passwd')\n"

CFG = {
    "name": "Same-defense adaptive attacks",
    "engine": "high_complexity",
    "roles": ["player_a", "player_b", "judge"],
    "judge_rubric": "r",
    "scoring_weights": {"phase1": 1.0},
    "exec_timeout_seconds": 60,
    "rounds": 3,
    "outcome_markers": ["SUCCESS", "FAIL"],
}


def test_fmt25_adaptive_wins_every_round():
    transport = FakeTransport()
    transport.model_replies = {"m-a": WIN_SUBMIT, "m-b": WIN_SUBMIT}
    transport.judge_result = {
        "scores": {"m-a": 50.0, "m-b": 50.0},
        "justifications": {},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    SameDefenseAdaptiveExecutor().run_battle(
        battle_id="b",
        format_config=CFG,
        model_ids=["m-a", "m-b"],
        round_visibility="open",
        timeout_seconds=60,
        role_to_model={"player_a": "m-a", "player_b": "m-b"},
        client=client,
    )
    events = [r for r in transport.rounds if r.get("event_type") == "result"]
    assert len(events) == 3
    r0 = json.loads(events[0]["artifact"].split(":", 1)[1])
    assert r0["player_a"] == "SUCCESS"
    assert r0["player_b"] == "SUCCESS"


def test_fmt25_smoke_round_harness():
    from pathlib import Path
    import tempfile
    from agent_arena.sandbox.executors.formats.same_defense_adaptive import (
        ROUND_HARNESS,
    )
    from agent_arena.sandbox.executors._harness import run_python, write_assets

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        write_assets(work, {"round.py": ROUND_HARNESS, "submit.py": WIN_SUBMIT})
        out, err, rc = run_python(
            work / "round.py", cwd=work, timeout=60, args=["submit.py", "3"]
        )
    assert rc == 0
    assert "ROUND0: SUCCESS" in out
    assert "ROUND2: SUCCESS" in out
