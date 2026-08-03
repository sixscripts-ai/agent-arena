import json

from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors.formats.arms_race import ArmsRaceExecutor

GOOD_ATTACK = (
    "import importlib.util as u\n"
    "spec = u.spec_from_file_location('svc', 'service.py')\n"
    "m = u.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "data = m.handle('secret.txt')\n"
    "print('GOT_FLAG' if data and 'FLAG{' in data else 'NOPE')\n"
)
GOOD_PATCH = (
    "def handle(request):\n"
    "    if not request.startswith('public/'):\n"
    "        return 'denied'\n"
    "    with open(request, 'r') as f:\n"
    "        return f.read()\n"
)

CFG = {
    "name": "Arms race",
    "engine": "high_complexity",
    "roles": ["player_a", "player_b", "judge"],
    "judge_rubric": "r",
    "scoring_weights": {"phase1": 1.0},
    "exec_timeout_seconds": 60,
    "rounds": 2,
    "service_code": "def handle(request):\n    with open(request, 'r') as f:\n        return f.read()\n",
    "secret": "FLAG{arms-race}",
    "outcome_markers": [
        "ATTACK_SUCCEEDED",
        "ATTACK_BLOCKED",
        "ATTACK_ALLOWED",
        "ATTACKER_WINS",
        "DEFENDER_WINS",
        "DRAW",
    ],
}


def test_fmt11_escalation_succeed_then_blocked():
    transport = FakeTransport()
    transport.model_replies = {"m-a": GOOD_ATTACK, "m-b": GOOD_PATCH}
    transport.judge_result = {
        "scores": {"m-a": 50.0, "m-b": 50.0},
        "justifications": {},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    ArmsRaceExecutor().run_battle(
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
    r1 = json.loads(events[0]["artifact"].split(":", 1)[1])
    r2 = json.loads(events[1]["artifact"].split(":", 1)[1])
    r3 = json.loads(events[2]["artifact"].split(":", 1)[1])
    assert r1["attacker"] == "ATTACK_SUCCEEDED"
    assert r2["attacker"] == "ATTACK_BLOCKED"
    assert r2["defender"] == "ATTACK_BLOCKED"
    assert r3["outcome"] == "DRAW"


def test_fmt11_smoke_harness_leaks_vulnerable_service():
    from pathlib import Path
    import tempfile
    from agent_arena.sandbox.executors.formats.arms_race import HARNESS
    from agent_arena.sandbox.executors._harness import run_python, write_assets

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        write_assets(
            work,
            {
                "harness.py": HARNESS,
                "attack.py": GOOD_ATTACK,
                "service.py": CFG["service_code"],
                "secret.txt": CFG["secret"],
            },
        )
        out, err, rc = run_python(work / "harness.py", cwd=work, timeout=60)
    assert rc == 0
    assert "OUTCOME: ATTACK_SUCCEEDED" in out
