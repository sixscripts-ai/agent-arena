import hashlib
import json
import re

from appwrite.query import Query

from . import db

ENGINE_TEMPLATES = {
    "build_and_break": {
        "roles": ["builder", "breaker", "judge"],
        "phases": [
            {"name": "build", "participants": ["builder"], "inputs": []},
            {"name": "break", "participants": ["breaker"], "inputs": ["build"]},
            {"name": "judge", "participants": ["judge"], "inputs": ["build", "break"]},
        ],
        "scoring_weights": {"build": 0.4, "break": 0.6},
    },
    "script_vs_defense": {
        "roles": ["attacker", "defender", "judge"],
        "phases": [
            {"name": "script", "participants": ["attacker"], "inputs": []},
            {"name": "defend", "participants": ["defender"], "inputs": ["script"]},
            {
                "name": "judge",
                "participants": ["judge"],
                "inputs": ["script", "defend"],
            },
        ],
        "scoring_weights": {"script": 0.5, "defend": 0.5},
    },
    "high_complexity": {
        "roles": ["player_a", "player_b", "judge"],
        "phases": [
            {"name": "phase1", "participants": ["player_a"], "inputs": []},
            {"name": "phase2", "participants": ["player_b"], "inputs": ["phase1"]},
            {
                "name": "phase3",
                "participants": ["player_a", "player_b"],
                "inputs": ["phase1", "phase2"],
            },
            {
                "name": "judge",
                "participants": ["judge"],
                "inputs": ["phase1", "phase2", "phase3"],
            },
        ],
        "scoring_weights": {"phase1": 0.2, "phase2": 0.3, "phase3": 0.5},
    },
}

RUBRICS = {
    "build_and_break": (
        "Judge whether the artifact built is functional and whether the breaker achieved "
        "a bypass. Award each side 0-100."
    ),
    "script_vs_defense": (
        "Judge whether the script is effective and whether the defense neutralizes it. "
        "Award each side 0-100."
    ),
    "high_complexity": "Judge multi-phase execution quality, adaptability, and final state. Award each side 0-100.",
}

FORMAT_DEFINITIONS = [
    (
        "WAF builder vs bypasser",
        "build_and_break",
        "Builder crafts a WAF rule set; breaker attempts to bypass.",
    ),
    (
        "Auth system vs breaker",
        "build_and_break",
        "Builder builds an auth system; breaker tries to break in.",
    ),
    (
        "Code sandbox vs escapee",
        "build_and_break",
        "Builder sandboxes code; escapee attempts escape.",
    ),
    (
        "Reverse shell vs network defense",
        "script_vs_defense",
        "Attacker crafts a reverse shell; defender hardens the network.",
    ),
    (
        "Payload generator vs detection",
        "script_vs_defense",
        "Attacker generates payloads; defender builds detection rules.",
    ),
    (
        "Arms race",
        "high_complexity",
        "Escalating multi-phase attack and defense arms race.",
    ),
    (
        "Credential hunt",
        "build_and_break",
        "Builder hides credentials in a service; hunter finds them.",
    ),
    ("Lock vs pick", "build_and_break", "Builder implements a lock; picker breaks it."),
    (
        "Polymorphic script vs signature defense",
        "script_vs_defense",
        "Attacker polymorphs a script; defender signatures it.",
    ),
    (
        "Credential-reuse script vs hardening",
        "script_vs_defense",
        "Attacker reuses leaked creds; defender hardens.",
    ),
    (
        "Exploit vs patch",
        "high_complexity",
        "Exploit development against iterative patching.",
    ),
    (
        "Time-limited siege",
        "high_complexity",
        "Multi-phase siege with a hard time limit.",
    ),
    (
        "Digital twin",
        "high_complexity",
        "Attack a realistic digital twin of a production system.",
    ),
    (
        "Same-defense adaptive attacks",
        "high_complexity",
        "Same defense, adaptively re-attacked across phases.",
    ),
]


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


FORMAT_EXTRA: dict[str, dict] = {
    # ---- Batch A: script_vs_defense ×4 + high_complexity ×5 ----
    "Reverse shell vs network defense": {
        "exec_timeout_seconds": 120,
        "c2_port": 38444,
        "outcome_markers": [
            "SHELL_ESTABLISHED",
            "SHELL_BLOCKED",
            "NO_CONNECTION",
            "DEFENDER_DETECTED",
            "DEFENDER_MISSED",
        ],
    },
    "Payload generator vs detection": {
        "exec_timeout_seconds": 120,
        "base_payloads": [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg/onload=alert(1)>",
            "javascript:alert(1)",
            '<iframe srcdoc="<script>alert(1)</script>"></iframe>',
        ],
        "benign_samples": [
            "hello world",
            "the quick brown fox",
            "SELECT name FROM users",
            "GET /index.html HTTP/1.1",
            "user@example.com",
        ],
        "outcome_markers": [
            "EVADED_ALL",
            "DETECTED_RATE_",
            "DETECTION_RATE_",
            "FALSE_POSITIVES_",
        ],
    },
    "Polymorphic script vs signature defense": {
        "exec_timeout_seconds": 120,
        "base_script": "import os\nprint('hello')\n",
        "variant_count": 6,
        "benign_scripts": [
            "print('hello')\n",
            "import math\nprint(math.pi)\n",
            "x = [i * i for i in range(10)]\nprint(x)\n",
        ],
        "outcome_markers": ["POLYMORPH_EVASION_RATE_", "DETECTION_RATE_"],
    },
    "Credential-reuse script vs hardening": {
        "exec_timeout_seconds": 120,
        "users": {"alice": _hash_password("alice123"), "bob": _hash_password("bobspw")},
        "creds": [
            "alice:password123",
            "bob:hunter2",
            "alice:letmein",
            "bob:password",
            "alice:admin",
            "bob:123456",
            "alice:alice123",
            "bob:bobspw",
        ],
        "outcome_markers": [
            "AUTH_OK",
            "LOCKED_OUT",
            "MFA_REQUIRED",
            "NO_SUCCESS",
            "COMPROMISED",
            "ATTACK_BLOCKED",
            "ATTACK_ALLOWED",
        ],
    },
    "Arms race": {
        "exec_timeout_seconds": 180,
        "rounds": 4,
        "service_code": (
            "def handle(request):\n"
            "    with open(request, 'r') as f:\n"
            "        return f.read()\n"
        ),
        "secret": "FLAG{arms-race}",
        "outcome_markers": [
            "ATTACK_SUCCEEDED",
            "ATTACK_BLOCKED",
            "ATTACK_ALLOWED",
            "ATTACKER_WINS",
            "DEFENDER_WINS",
            "DRAW",
        ],
    },
    "Exploit vs patch": {
        "exec_timeout_seconds": 180,
        "service_code": (
            "def handle(request):\n"
            "    with open(request, 'r') as f:\n"
            "        return f.read()\n"
        ),
        "flag": "FLAG{exploit-vs-patch}",
        "outcome_markers": ["EXPLOITED", "FAILED", "PATCHED", "BYPASSED"],
    },
    "Time-limited siege": {
        "exec_timeout_seconds": 180,
        "layers": ["abcd", "bcde", "cdef"],
        "layer_budget_s": 20,
        "outcome_markers": ["LAYERS_BREACHED_", "LAYERS_DEFENDED_"],
    },
    "Digital twin": {
        "exec_timeout_seconds": 120,
        "twin_code": (
            "import json\n"
            "def handle(command):\n"
            "    with open('twin.log', 'a') as f:\n"
            "        f.write(json.dumps(command) + '\\n')\n"
            "    if command['op'] == 'TRANSFER':\n"
            "        return 'ok'\n"
            "    if command['op'] == 'BALANCE':\n"
            "        return 'balance:1000'\n"
            "    if command['op'] == 'READ_SECRET':\n"
            "        return open('secret.txt').read().strip()\n"
            "    return 'unknown'\n"
        ),
        "secret": "FLAG{digital-twin}",
        "outcome_markers": ["IMPACT_", "DETECTED_"],
    },
    "Same-defense adaptive attacks": {
        "exec_timeout_seconds": 120,
        "rounds": 3,
        "outcome_markers": ["SUCCESS", "FAIL"],
    },
}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:36]


def build_format(
    name: str, engine: str, description: str, extra: dict | None = None
) -> dict:
    template = ENGINE_TEMPLATES[engine]
    cfg = {
        "id": _slugify(name),
        "name": name,
        "engine": engine,
        "description": description,
        "roles": template["roles"],
        "phases": template["phases"],
        "sandbox_image": "python:3.11-slim",
        "timeout_seconds": 600,
        "round_visibility": "isolated",
        "judge_rubric": RUBRICS[engine],
        "scoring_weights": template["scoring_weights"],
    }
    if extra:
        cfg.update(extra)
    return cfg


ALL_FORMATS = [
    build_format(n, e, d, extra=FORMAT_EXTRA.get(n)) for n, e, d in FORMAT_DEFINITIONS
]


def seed_formats() -> int:
    databases = db.get_databases()
    database_id = db.get_database_id()
    count = 0
    for cfg in ALL_FORMATS:
        res = databases.list_documents(
            database_id,
            "formats",
            queries=[Query.equal("name", cfg["name"]), Query.limit(1)],
        )
        payload = {
            "name": cfg["name"],
            "engine": cfg["engine"],
            "config": json.dumps(cfg),
        }
        if res.documents:
            databases.update_document(
                database_id, "formats", res.documents[0].id, payload
            )
        else:
            databases.create_document(database_id, "formats", "unique()", payload)
        count += 1
    return count
