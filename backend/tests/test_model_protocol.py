import json

import httpx
import pytest
from fastapi import HTTPException

from agent_arena.llm_client import chat_completion_result
from agent_arena.model_protocol import (
    ModelResult,
    classify_provider_error,
    model_capabilities,
    normalize_tool_calls,
    parse_openai_response,
)
from agent_arena.sandbox.executors.advanced_executor import AdvancedExecutor
from tests.test_advanced_executor import PALINDROME_TOOLS


def _tc(name, args, call_id="call_1"):
    arguments = args if isinstance(args, str) else json.dumps(args)
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def _native_solve(skill="python-kata-fixer"):
    sol = (
        "def is_palindrome(s: str) -> bool:\n"
        "    n = ''.join(c.lower() for c in s if c.isalnum())\n"
        "    return n == n[::-1]\n"
    )
    return {
        "content": None,
        "finish_reason": "tool_calls",
        "provider": "OpenRouter",
        "model": "openai/gpt-oss-20b",
        "tool_calls": [
            _tc("skills", {"chosen": [skill]}, "c0"),
            _tc("use_skill", {"name": skill}, "c1"),
            _tc("read", {"path": "TARGET.md"}, "c2"),
            _tc("write", {"path": "solution.py", "content": sol}, "c3"),
            _tc("write", {"path": "THEORY.md", "content": "used skill"}, "c4"),
            _tc("test", {}, "c5"),
        ],
    }


def _race_cfg(**extra):
    cfg = {
        "name": "Tool-using coding race",
        "engine": "agent_tool_race",
        "roles": ["player_a", "player_b", "judge"],
        "phases": [{"name": "race", "participants": ["player_a", "player_b"]}],
        "target_code": "def is_palindrome(s): return s == s[::-1]\n",
        "max_tool_turns": 4,
        "max_tool_steps": 20,
        "pick_per_battle": 1,
        "outcome_markers": ["DONE", "TEST_PASS", "TEST_FAIL"],
    }
    cfg.update(extra)
    return cfg


def _run(monkeypatch, replies, cfg=None, **transport_kw):
    from agent_arena.sandbox.client import FakeTransport, InternalClient

    monkeypatch.setenv("ARENA_IN_SANDBOX", "1")
    transport = FakeTransport()
    transport.model_replies = replies
    for key, value in transport_kw.items():
        setattr(transport, key, value)
    mids = list(replies)
    transport.judge_result = {
        "scores": {mid: 70.0 + i for i, mid in enumerate(mids)},
        "justifications": {mid: "ok" for mid in mids},
        "judge_model": "mock",
    }
    client = InternalClient(transport)
    roles = ["player_a", "player_b"][: len(mids)]
    role_to_model = dict(zip(roles, mids))
    scores = AdvancedExecutor().run_battle(
        battle_id="proto-1",
        format_config=cfg or _race_cfg(),
        model_ids=mids,
        round_visibility="isolated",
        timeout_seconds=60,
        role_to_model=role_to_model,
        client=client,
    )
    return transport, scores


def test_native_tool_calls_content_null():
    data = {
        "provider": "OpenRouter",
        "model": "openai/gpt-oss-20b",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [_tc("ls", {"path": "."}, "call_ls")],
                },
            }
        ],
    }
    result = parse_openai_response(data)
    assert result.content == ""
    assert result.finish_reason == "tool_calls"
    assert result.provider == "OpenRouter"
    assert result.model == "openai/gpt-oss-20b"
    assert result.tool_calls[0]["id"] == "call_ls"
    calls, err = normalize_tool_calls(result)
    assert err is None
    assert calls[0]["tool"] == "ls"
    assert calls[0]["id"] == "call_ls"


def test_openrouter_structured_tool_calls():
    data = {
        "provider": "OpenRouter",
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "or-1",
                            "index": 0,
                            "type": "function",
                            "function": {
                                "name": "read",
                                "arguments": '{"path":"TARGET.md"}',
                            },
                        }
                    ],
                },
            }
        ],
    }
    result = parse_openai_response(data)
    calls, err = normalize_tool_calls(result)
    assert err is None
    assert calls == [{"tool": "read", "id": "or-1", "path": "TARGET.md"}]


def test_multiple_native_tool_calls_one_response():
    result = ModelResult(
        content="",
        finish_reason="tool_calls",
        tool_calls=[
            _tc("ls", {"path": "."}, "a"),
            _tc("read", {"path": "TARGET.md"}, "b"),
            _tc("test", {}, "c"),
        ],
    )
    calls, err = normalize_tool_calls(result)
    assert err is None
    assert [c["tool"] for c in calls] == ["ls", "read", "test"]
    assert [c["id"] for c in calls] == ["a", "b", "c"]


def test_json_content_fallback():
    result = ModelResult(content='{"tool":"read","path":"TARGET.md"}')
    calls, err = normalize_tool_calls(result)
    assert err is None
    assert calls[0]["tool"] == "read"
    assert calls[0]["path"] == "TARGET.md"


def test_textual_tool_fallback():
    result = ModelResult(content="TOOL ls path=.\nTOOL read path=TARGET.md\n")
    calls, err = normalize_tool_calls(result)
    assert err is None
    assert [c["tool"] for c in calls] == ["ls", "read"]


def test_invalid_arguments_typed_error():
    result = ModelResult(
        content="",
        finish_reason="tool_calls",
        tool_calls=[_tc("read", "{not-json", "bad")],
    )
    calls, err = normalize_tool_calls(result)
    assert calls[0]["error"] == "invalid_arguments"
    assert calls[0]["id"] == "bad"
    assert err and "invalid_arguments" in err


def test_prose_is_not_a_tool_call():
    calls, err = normalize_tool_calls(ModelResult(content="I will solve this in prose."))
    assert calls == []
    assert err


def test_repair_then_valid_tool_call(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {
            "a": ["thinking out loud", PALINDROME_TOOLS],
            "b": [PALINDROME_TOOLS],
        },
        cfg=_race_cfg(max_tool_turns=4),
    )
    arts = " ".join(r.get("artifact", "") for r in transport.rounds)
    assert "No TOOL calls" in arts
    assert "python-kata-fixer" in arts
    a_models = [
        body
        for path, body in transport.calls
        if path == "/internal/model" and body.get("model_id") == "a"
    ]
    assert len(a_models) >= 2
    assert any("had no valid tool call" in str(m.get("messages")) for m in a_models)


def test_two_no_tool_responses_fail_participant(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": ["prose one", "prose two", "prose three"], "b": ["x", "y", "z"]},
        cfg=_race_cfg(max_tool_turns=6),
    )
    failed = [r for r in transport.rounds if r.get("event_type") == "participant_failed"]
    assert len(failed) == 2
    assert all("no_tool_exhaustion" in r.get("artifact", "") for r in failed)
    a_calls = [
        b for p, b in transport.calls if p == "/internal/model" and b.get("model_id") == "a"
    ]
    assert len(a_calls) == 2


def test_agent_a_fails_while_b_continues(monkeypatch):
    transport, scores = _run(
        monkeypatch,
        {"a": ["nope", "still nope"], "b": [_native_solve()]},
        cfg=_race_cfg(max_tool_turns=4),
    )
    types = {(r.get("model_id"), r.get("event_type")) for r in transport.rounds}
    assert ("a", "participant_failed") in types
    arts = " ".join(r.get("artifact", "") for r in transport.rounds)
    assert "python-kata-fixer" in arts
    assert scores["b"] >= 70


def test_both_participants_start_without_serial_starvation(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": [_native_solve()], "b": [_native_solve()]},
        cfg=_race_cfg(max_tool_turns=2),
        model_delay_s=0.2,
    )
    starts = [r for r in transport.rounds if r.get("event_type") == "participant_start"]
    assert {r.get("model_id") for r in starts} == {"a", "b"}
    assert len(transport.model_started) >= 2
    delta = abs(transport.model_started[0][1] - transport.model_started[1][1])
    assert delta < 0.15


def test_provider_timeout_fails_only_that_participant(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": [_native_solve()], "b": [_native_solve()]},
        timeout_models={"a"},
    )
    arts = " ".join(r.get("artifact", "") for r in transport.rounds)
    assert "provider_timeout" in arts
    failed = [r for r in transport.rounds if r.get("event_type") == "participant_failed"]
    assert any(r.get("model_id") == "a" for r in failed)
    a_nudges = [
        r
        for r in transport.rounds
        if r.get("model_id") == "a" and "No TOOL calls" in (r.get("artifact") or "")
    ]
    assert a_nudges == []
    assert any(
        r.get("model_id") == "b" and "python-kata-fixer" in (r.get("artifact") or "")
        for r in transport.rounds
    )


def test_quota_exhausted_is_not_no_tool(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": ["should not be used"], "b": [_native_solve()]},
        quota_models={"a"},
    )
    arts = " ".join(r.get("artifact", "") for r in transport.rounds)
    assert "provider_quota_exhausted" in arts
    a_nudges = [
        r
        for r in transport.rounds
        if r.get("model_id") == "a" and "No TOOL calls" in (r.get("artifact") or "")
    ]
    assert a_nudges == []
    assert classify_provider_error(RuntimeError("provider_quota_exhausted")) == (
        "provider_quota_exhausted"
    )


def test_tool_result_returned_to_same_model(monkeypatch):
    first = {
        "content": None,
        "finish_reason": "tool_calls",
        "tool_calls": [_tc("ls", {"path": "."}, "call_ls")],
        "provider": "groq",
        "model": "llama",
    }
    transport, _ = _run(
        monkeypatch,
        {"a": [first, _native_solve()], "b": [_native_solve()]},
        cfg=_race_cfg(max_tool_turns=4),
    )
    a_calls = [
        b for p, b in transport.calls if p == "/internal/model" and b.get("model_id") == "a"
    ]
    assert len(a_calls) >= 2
    second_msgs = a_calls[1]["messages"]
    assert any(m.get("role") == "assistant" and m.get("tool_calls") for m in second_msgs)
    tool_msgs = [m for m in second_msgs if m.get("role") == "tool"]
    assert tool_msgs
    assert tool_msgs[0]["tool_call_id"] == "call_ls"
    assert tool_msgs[0]["name"] == "ls"
    assert "content" in tool_msgs[0]


def test_runtime_selected_proves_advanced_executor(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": [PALINDROME_TOOLS], "b": [PALINDROME_TOOLS]},
        cfg=_race_cfg(max_tool_turns=2),
    )
    selected = [r for r in transport.rounds if r.get("event_type") == "runtime_selected"]
    assert selected
    payload = json.loads(selected[0]["artifact"])
    assert payload["executor"] == "AdvancedExecutor"
    assert payload["format_engine"] == "agent_tool_race"
    assert payload["universal"] is True


def test_native_tools_passed_through_internal_model(monkeypatch):
    transport, _ = _run(
        monkeypatch,
        {"a": [_native_solve()], "b": [_native_solve()]},
        cfg=_race_cfg(max_tool_turns=2),
    )
    model_bodies = [b for p, b in transport.calls if p == "/internal/model"]
    assert model_bodies
    assert model_bodies[0].get("tools")
    names = {t["function"]["name"] for t in model_bodies[0]["tools"]}
    assert {"ls", "read", "write", "test", "use_skill"} <= names
    assert model_bodies[0].get("tool_choice") == "auto"


def test_llm_client_preserves_null_content_and_tool_calls(monkeypatch):
    class _Resp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "provider": "Groq",
                "model": "llama-3.3-70b-versatile",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": None,
                            "tool_calls": [_tc("ls", {"path": "workspace"}, "g1")],
                        },
                    }
                ],
            }

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    result = chat_completion_result(
        base_url="https://api.groq.com/openai/v1",
        auth_style="bearer",
        api_key="gsk_test",
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "ls"}],
        tools=[{"type": "function", "function": {"name": "ls", "parameters": {}}}],
    )
    assert result.content == ""
    assert result.finish_reason == "tool_calls"
    assert result.tool_calls[0]["function"]["name"] == "ls"
    assert result.provider == "Groq"


def test_llm_client_429_is_quota_not_empty_content(monkeypatch):
    class _Resp:
        status_code = 429
        text = "Rate limit exceeded: free-models-per-day"

        def json(self):
            return {"error": {"message": self.text}}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(HTTPException) as exc:
        chat_completion_result(
            base_url="https://openrouter.ai/api/v1",
            auth_style="bearer",
            api_key="sk-or-test",
            model="openai/gpt-oss-20b:free",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert exc.value.status_code == 429
    assert exc.value.detail == "provider_quota_exhausted"


def test_model_capabilities_gemma_text_only():
    caps = model_capabilities("host:or-gemma-31b")
    assert caps["supports_tools"] is False
    assert caps["supports_text_tools"] is True
    assert model_capabilities("host:groq-llama")["supports_tools"] is True
