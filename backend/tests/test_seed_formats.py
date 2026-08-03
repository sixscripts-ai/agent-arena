from agent_arena.seed_formats import (
    ENGINE_TEMPLATES,
    FORMAT_DEFINITIONS,
    build_format,
)


def test_exactly_twenty_five_formats():
    assert len(FORMAT_DEFINITIONS) == 25


def test_all_six_engines_covered():
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


def test_build_format_shape():
    cfg = build_format(
        "Code review duel", "same_target_race", "Two reviewers on one target"
    )
    assert cfg["id"] == "code-review-duel"
    assert cfg["engine"] == "same_target_race"
    assert cfg["sandbox_image"] == "python:3.11-slim"
    assert cfg["timeout_seconds"] == 600
    assert cfg["round_visibility"] == "isolated"
    assert set(["roles", "phases", "judge_rubric", "scoring_weights"]) <= set(cfg)


def test_ids_are_unique():
    ids = [build_format(n, e, d)["id"] for n, e, d in FORMAT_DEFINITIONS]
    assert len(ids) == len(set(ids))


def test_extra_merged_into_config():
    cfg = build_format(
        "Reverse shell vs network defense",
        "script_vs_defense",
        "d",
        extra={"outcome_markers": ["SHELL_ESTABLISHED"], "exec_timeout_seconds": 90},
    )
    assert cfg["outcome_markers"] == ["SHELL_ESTABLISHED"]
    assert cfg["exec_timeout_seconds"] == 90
    assert cfg["engine"] == "script_vs_defense"


def test_batch_a_extras_present_for_all_nine():
    from agent_arena.seed_formats import FORMAT_EXTRA

    names = [
        "Reverse shell vs network defense",
        "Payload generator vs detection",
        "Polymorphic script vs signature defense",
        "Credential-reuse script vs hardening",
        "Arms race",
        "Exploit vs patch",
        "Time-limited siege",
        "Digital twin",
        "Same-defense adaptive attacks",
    ]
    for n in names:
        assert n in FORMAT_EXTRA, n
        assert "outcome_markers" in FORMAT_EXTRA[n]
