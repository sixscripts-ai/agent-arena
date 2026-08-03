import json

from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors.formats.payload_vs_detection import (
    PayloadVsDetectionExecutor,
)

ALLOW_ALL = "import sys\nfor _ in open(sys.argv[1]):\n    print('ALLOW')\n"
BLOCK_SCRIPT = (
    "import sys\n"
    "for line in open(sys.argv[1]):\n"
    "    print('BLOCK' if 'script' in line.lower() else 'ALLOW')\n"
)
GOOD_GENERATE = (
    "payloads = open('base_payloads.txt').read().splitlines()\n"
    "with open('variants.txt', 'w') as f:\n"
    "    for i, p in enumerate(payloads):\n"
    "        f.write(p.upper() + '\\n')\n"
)

CFG = {
    "name": "Payload generator vs detection",
    "engine": "script_vs_defense",
    "roles": ["attacker", "defender", "judge"],
    "judge_rubric": "r",
    "scoring_weights": {"script": 0.5, "defend": 0.5},
    "exec_timeout_seconds": 60,
    "base_payloads": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"],
    "benign_samples": ["hello world", "the quick brown fox"],
    "outcome_markers": [
        "EVADED_ALL",
        "DETECTED_RATE_",
        "DETECTION_RATE_",
        "FALSE_POSITIVES_",
    ],
}


def _run(detect: str):
    transport = FakeTransport()
    transport.model_replies = {"m-att": GOOD_GENERATE, "m-def": detect}
    transport.judge_result = {
        "scores": {"m-att": 50.0, "m-def": 50.0},
        "justifications": {},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    PayloadVsDetectionExecutor().run_battle(
        battle_id="b",
        format_config=CFG,
        model_ids=["m-att", "m-def"],
        round_visibility="isolated",
        timeout_seconds=60,
        role_to_model={"attacker": "m-att", "defender": "m-def"},
        client=client,
    )
    events = [r for r in transport.rounds if r.get("event_type") == "result"]
    return json.loads(events[0]["artifact"].split(":", 1)[1])


def test_fmt05_all_evaded():
    result = _run(ALLOW_ALL)
    assert result["attacker"] == "EVADED_ALL"
    assert result["defender"] == "DETECTION_RATE_0"
    assert result["false_positives"] == "FALSE_POSITIVES_0"


def test_fmt05_detection_rate_and_fp():
    result = _run(BLOCK_SCRIPT)
    assert result["attacker"] == "DETECTED_RATE_50"
    assert result["defender"] == "DETECTION_RATE_50"
    assert result["false_positives"] == "FALSE_POSITIVES_0"


def test_fmt05_smoke_classify_harness():
    from pathlib import Path
    import tempfile
    from agent_arena.sandbox.executors.formats.payload_vs_detection import (
        CLASSIFY_HARNESS,
    )
    from agent_arena.sandbox.executors._harness import run_python, write_assets

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        write_assets(
            work,
            {
                "classify.py": CLASSIFY_HARNESS,
                "detect.py": BLOCK_SCRIPT,
                "variants.txt": "<SCRIPT>ALERT(1)</SCRIPT>\n<img src=x onerror=alert(1)>\n",
                "benign.txt": "hello world\n",
            },
        )
        out, err, rc = run_python(work / "classify.py", cwd=work, timeout=60)
    assert rc == 0
    assert "OUTCOME: DETECTION_RATE_50" in out
    assert "FALSE_POSITIVES=0" in out
