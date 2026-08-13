"""C8 skill loader/validator + C10 selection protocol (hermetic)."""

from pathlib import Path

import pytest

from agent_arena.sandbox.executors.advanced_executor import (
    MAX_SELECTED_SKILLS,
    select_skills,
)
from agent_arena.sandbox.executors.skill_pool import (
    filter_skills,
    list_skills,
    load_skill,
    resolve_prerequisites,
    validate_skill,
)

GOOD_SKILL = """---
name: test-skill
description: does useful things in the arena
metadata:
  version: "0.1.0"
  category: testing
  tags: "testing,arena"
  tier: general
capabilities: shell, write, test
prerequisites: shell-basics
---
# body
steps
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(content, encoding="utf-8")
    return d


def test_validate_skill_good_and_bad():
    assert validate_skill(GOOD_SKILL, "test-skill") == []
    errs = validate_skill("no frontmatter at all", "bad")
    assert any("frontmatter" in e for e in errs)
    assert any("description" in e for e in errs)


def test_load_skill_by_slug_and_list_filter(tmp_path):
    _write(
        tmp_path,
        "shell-basics",
        "---\nname: shell-basics\ndescription: fundamentals\ntier: novice\n---\nbody\n",
    )
    _write(
        tmp_path,
        "payload-obfuscator",
        GOOD_SKILL.replace("test-skill", "payload-obfuscator").replace(
            "testing", "cyber"
        ),
    )
    s = load_skill("payload-obfuscator", tmp_path)
    assert s["name"] == "payload-obfuscator"
    assert s["tier"] == "general"
    assert "shell" in s["capabilities"]
    names = [x["name"] for x in filter_skills("obfusc", root=tmp_path)]
    assert names == ["payload-obfuscator"]


def test_resolve_prerequisites(tmp_path):
    _write(
        tmp_path,
        "shell-basics",
        "---\nname: shell-basics\ndescription: fundamentals\n---\nbody\n",
    )
    _write(
        tmp_path,
        "payload-obfuscator",
        GOOD_SKILL.replace("test-skill", "payload-obfuscator"),
    )
    pool = list_skills(tmp_path)
    chosen = [s for s in pool if s["name"] == "payload-obfuscator"]
    assert resolve_prerequisites(chosen, pool) == ["shell-basics"]


def test_select_skills_respects_recommended_and_cap(tmp_path):
    for name in ("shell-basics", "python-kata-fixer", "waf-bypass"):
        _write(
            tmp_path,
            name,
            f"---\nname: {name}\ndescription: a skill for {name}\ntier: general\n---\nbody\n",
        )
    pool = list_skills(tmp_path)
    cfg = {"name": "WAF battle", "recommended_skills": ["waf-bypass"]}
    sel = select_skills(cfg, pool)
    assert sel[0]["name"] == "waf-bypass"
    cfg2 = {}
    assert len(select_skills(cfg2, pool)) <= MAX_SELECTED_SKILLS


def test_list_skills_returns_known_fields(tmp_path):
    _write(
        tmp_path,
        "python-kata-fixer",
        GOOD_SKILL.replace("test-skill", "python-kata-fixer"),
    )
    pool = list_skills(tmp_path)
    assert pool
    assert all(
        {"name", "desc", "elo", "tier", "tags", "capabilities", "body"} <= set(s)
        for s in pool
    )
