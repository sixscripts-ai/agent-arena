import json

from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors import get_executor
from agent_arena.sandbox.executors.scripted import ScriptedExecutor
from agent_arena.sandbox.executors.build_and_break import BuildAndBreakExecutor


class PhaseExecutor:
    """run_phase-only executor; base.run_battle must drive it via the phase loop."""

    def run_phase(
        self,
        *,
        client,
        battle_id,
        phase,
        role_to_model,
        history,
        format_config,
        round_visibility,
    ):
        mid = role_to_model[phase["participants"][0]]
        content = client.model(battle_id, mid, [], phase=phase["name"])
        art = {"phase": phase["name"], "model_id": mid, "artifact": content}
        client.round(battle_id, phase["name"], mid, content)
        return [art]


def test_get_executor_falls_back_to_engine_when_unmigrated():
    cfg = {"name": "Not yet migrated", "engine": "build_and_break"}
    assert isinstance(get_executor(cfg), BuildAndBreakExecutor)


def test_get_executor_falls_back_to_scripted_for_unknown_engine():
    cfg = {"name": "x", "engine": "nope"}
    assert isinstance(get_executor(cfg), ScriptedExecutor)


def test_base_run_battle_runs_phase_loop_and_returns_scores():
    transport = FakeTransport()
    transport.model_replies = {"m1": "move-a"}
    transport.judge_result = {
        "scores": {"m1": 61.0, "m2": 39.0},
        "justifications": {"m1": "ok", "m2": "no"},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    cfg = {
        "name": "t",
        "engine": "direct_duel",
        "roles": ["player_a", "player_b", "judge"],
        "phases": [{"name": "p1", "participants": ["player_a"]}],
        "judge_rubric": "r",
        "scoring_weights": {"p1": 1.0},
    }
    scores = get_executor(cfg).run_battle(
        battle_id="b",
        format_config=cfg,
        model_ids=["m1", "m2"],
        round_visibility="open",
        timeout_seconds=60,
        role_to_model={"player_a": "m1", "player_b": "m2"},
        client=client,
    )
    assert scores == {"m1": 61.0, "m2": 39.0}
    assert any(p == "/internal/model" for p, _ in transport.calls)
    assert any(p == "/internal/judge" for p, _ in transport.calls)


def test_emit_result_publishes_result_event_and_returns_line():
    transport = FakeTransport()
    client = InternalClient(transport)
    from agent_arena.sandbox.executors.base import Executor

    line = Executor.emit_result(client, "b", "judge", {"attacker": "SHELL_BLOCKED"})
    assert line.startswith("EXECUTOR_RESULT: ")
    assert json.loads(line.split(":", 1)[1]) == {"attacker": "SHELL_BLOCKED"}
    result_events = [r for r in transport.rounds if r.get("event_type") == "result"]
    assert len(result_events) == 1
    assert result_events[0]["model_id"] == "system"
    assert result_events[0]["phase"] == "judge"
    assert "SHELL_BLOCKED" in result_events[0]["artifact"]


def test_guard_exact_and_prefix():
    from agent_arena.sandbox.executors.base import Executor

    markers = ["EVADED_ALL", "DETECTION_RATE_", "FALSE_POSITIVES_"]
    assert Executor.guard("evaded_all", markers) == "EVADED_ALL"
    assert Executor.guard("detection_rate_42", markers) == "DETECTION_RATE_42"
    assert Executor.guard("BOGUS", markers) == "INCONCLUSIVE"
    assert Executor.guard(5, markers) == 5  # non-strings pass through


def test_get_executor_resolves_bespoke_by_name():
    from agent_arena.sandbox.executors.formats.rev_shell_vs_defense import (
        RevShellVsDefenseExecutor,
    )

    cfg = {"name": "Reverse shell vs network defense", "engine": "script_vs_defense"}
    assert isinstance(get_executor(cfg), RevShellVsDefenseExecutor)


def test_get_executor_resolves_bespoke_by_slug():
    from agent_arena.sandbox.executors.formats.rev_shell_vs_defense import (
        RevShellVsDefenseExecutor,
    )

    cfg = {"id": "reverse-shell-vs-network-defense", "engine": "script_vs_defense"}
    assert isinstance(get_executor(cfg), RevShellVsDefenseExecutor)
