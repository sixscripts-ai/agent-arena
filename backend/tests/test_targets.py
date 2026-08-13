"""D11 targets library loading + validation (hermetic)."""

from pathlib import Path

import pytest

from agent_arena.seed_targets import load_targets

CYBER_ROOT = Path(__file__).resolve().parents[2] / "targets"


def test_loads_cyber_targets():
    targets = load_targets(CYBER_ROOT)
    assert targets, "targets/ directory should contain YAML targets"
    cyber = [t for t in targets if t["category"] == "cyber"]
    assert cyber, "expected cyber targets"
    for t in targets:
        assert t["id"]
        assert t["target_code"]
        assert t["test_code"]
        # synthetic-only guarantee: every target declares it is simulated/sandboxed
        marker = t["target_code"] + " " + t["description"]
        assert "SIMULATED" in marker or "FLAG{" in marker or "sandbox" in marker.lower()


def test_rejects_bad_target(tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "id: x\nname: missing target code\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        load_targets(tmp_path)


def test_rejects_unknown_fields(tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "id: x\ncategory: cyber\ntarget_code: pass\ntest_code: pass\nnonsense: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_targets(tmp_path)
