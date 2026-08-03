from __future__ import annotations
import pathlib

# Additive patch for seed_formats.py - mirrors mission spec
# This script is idempotent and checks for existing entries

def patch():
    p = pathlib.Path("/Users/villain/modal/backend/agent_arena/seed_formats.py")
    text = p.read_text()
    changed = False

    if '"agent_tool_race"' not in text:
        # Insert ENGINE_TEMPLATES
        old = '''    "agent_vs_agent": {
        "roles": ["agent_a", "agent_b", "judge"],
        "phases": [
            {"name": "engage", "participants": ["agent_a", "agent_b"], "inputs": []},
            {"name": "judge", "participants": ["judge"], "inputs": ["engage"]},
        ],
        "scoring_weights": {"engage": 1.0},
    },
}

RUBRICS = {'''
        new = '''    "agent_vs_agent": {
        "roles": ["agent_a", "agent_b", "judge"],
        "phases": [
            {"name": "engage", "participants": ["agent_a", "agent_b"], "inputs": []},
            {"name": "judge", "participants": ["judge"], "inputs": ["engage"]},
        ],
        "scoring_weights": {"engage": 1.0},
    },
    "agent_tool_race": {
        "roles": ["player_a", "player_b", "judge"],
        "phases": [
            {"name": "race", "participants": ["player_a", "player_b"], "inputs": []},
            {"name": "judge", "participants": ["judge"], "inputs": ["race"]},
        ],
        "scoring_weights": {"race": 1.0},
    },
}

RUBRICS = {'''
        if old in text:
            text = text.replace(old, new)
            changed = True
            print("Patched ENGINE_TEMPLATES")

    if '"agent_tool_race": "Judge correctness' not in text:
        old = '"agent_vs_agent": "Judge which agent better achieved its mission across the engagement. Award each side 0-100.",\n}\n\nFORMAT_DEFINITIONS'
        new = '"agent_vs_agent": "Judge which agent better achieved its mission across the engagement. Award each side 0-100.",\n    "agent_tool_race": "Judge correctness vs the shared target, test coverage, efficiency, and final workspace state. Award each side 0-100.",\n}\n\nFORMAT_DEFINITIONS'
        if old in text:
            text = text.replace(old, new)
            changed = True
            print("Patched RUBRICS")

    # FORMAT_DEFINITIONS etc handled similarly in full implementation
    if changed:
        p.write_text(text)
        print("Wrote patched seed_formats.py")

if __name__ == "__main__":
    patch()
