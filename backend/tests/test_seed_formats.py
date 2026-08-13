from agent_arena.seed_formats import (
    ENGINE_TEMPLATES,
    FORMAT_DEFINITIONS,
    build_format,
)


def test_exactly_twenty_six_formats():
    assert len(FORMAT_DEFINITIONS) == 26


def test_all_engines_covered():
    engines = {eng for _, eng, _ in FORMAT_DEFINITIONS}
    assert engines == set(ENGINE_TEMPLATES)


def test_flag_ship_names_present():
    names = {name for name, _, _ in FORMAT_DEFINITIONS}
    assert "WAF builder vs bypasser" in names
    assert "Two-agent duel" in names


def test_user_selected_names_present():
    names = {name for name, _, _ in FORMAT_DEFINITIONS}
    assert "Pwn exploit race" in names
    assert "Same-defense adaptive attacks" in names
    assert "Tool-using coding race" in names


def test_build_format_shape():
    cfg = build_format("Code review duel", "same_target_race", "Two reviewers on one target")
    assert cfg["id"] == "code-review-duel"
    assert cfg["engine"] == "same_target_race"
    assert cfg["sandbox_image"] == "python:3.11-slim"
    assert cfg["timeout_seconds"] == 600
    assert cfg["round_visibility"] == "isolated"
    assert set(["roles", "phases", "judge_rubric", "scoring_weights"]) <= set(cfg)


def test_ids_are_unique():
    ids = [build_format(n, e, d)["id"] for n, e, d in FORMAT_DEFINITIONS]
    assert len(ids) == len(set(ids))
