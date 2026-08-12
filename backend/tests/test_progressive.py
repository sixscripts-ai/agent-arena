from agent_arena.sandbox.client import FakeTransport, InternalClient
from agent_arena.sandbox.executors.direct_duel import DirectDuelExecutor
from agent_arena.sandbox.executors.progressive import (
    build_phase_context,
    is_stagnant,
)
from agent_arena.sandbox.executors.same_target_race import SameTargetRaceExecutor


def _model_calls(transport: FakeTransport):
    return [body for path, body in transport.calls if path == "/internal/model"]


def test_is_stagnant_detects_near_copy_but_not_real_revision():
    old = "def solve():\n    return 'same implementation'\n" * 8
    near = "def solve():\n    return 'same implementation'\n" * 8
    changed = "def solve():\n    # materially different strategy\n    return sum(range(100))\n" * 8
    assert is_stagnant(old, near)
    assert not is_stagnant(old, changed)


def test_declared_inputs_visible_even_when_isolated():
    history = [
        {"phase": "build", "model_id": "m1", "artifact": "builder artifact"},
        {"phase": "other", "model_id": "m1", "artifact": "hidden unrelated artifact"},
    ]
    ctx = build_phase_context(
        history,
        model_id="m2",
        input_phases=["build"],
        round_visibility="isolated",
    )
    assert "builder artifact" in ctx
    assert "hidden unrelated artifact" not in ctx


def test_direct_duel_second_turn_sees_opponent_even_in_isolated_mode():
    transport = FakeTransport()
    transport.model_replies = {"m1": "attack move", "m2": "defense move"}
    client = InternalClient(transport)
    ex = DirectDuelExecutor()
    ex.run_phase(
        client=client,
        battle_id="b",
        phase={"name": "duel", "participants": ["a", "b"]},
        role_to_model={"a": "m1", "b": "m2"},
        history=[],
        format_config={"name": "adaptive duel", "duel_turns": 2},
        round_visibility="isolated",
    )
    calls = _model_calls(transport)
    m1_calls = [c for c in calls if c["model_id"] == "m1"]
    assert len(m1_calls) >= 2
    second_prompt = m1_calls[-1]["messages"][-1]["content"]
    assert "defense move" in second_prompt
    assert "Your previous move" in second_prompt


def test_same_target_race_runs_progressive_iterations_with_previous_artifact():
    transport = FakeTransport()
    transport.model_replies = {
        "m1": "Fix the bug with assert and tests.",
        "m2": "Review the bug and add assert coverage.",
    }
    client = InternalClient(transport)
    ex = SameTargetRaceExecutor()
    arts = ex.run_phase(
        client=client,
        battle_id="b",
        phase={"name": "race", "participants": ["a", "b"]},
        role_to_model={"a": "m1", "b": "m2"},
        history=[],
        format_config={"name": "debug race", "race_turns": 2},
        round_visibility="open",
    )
    assert len(arts) == 4
    calls = _model_calls(transport)
    second_round_calls = [c for c in calls if "Iteration 2/2" in c["messages"][0]["content"]]
    assert second_round_calls
    assert any("YOUR PREVIOUS ARTIFACT" in c["messages"][1]["content"] for c in second_round_calls)
    assert any("OPPONENT LATEST ARTIFACT" in c["messages"][1]["content"] for c in second_round_calls)
