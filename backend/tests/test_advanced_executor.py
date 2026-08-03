from agent_arena.sandbox.executors.advanced_executor import parse_tool_calls, ToolSession, SKILL_POOL
from pathlib import Path

def test_parse_tool_calls_single_line():
    calls = parse_tool_calls("TOOL ls path=work\nTOOL read path=sandbox.py\nDONE")
    assert calls[0]["tool"] == "ls"
    assert calls[0]["path"] == "work"
    assert calls[1]["tool"] == "read"
    assert calls[2]["tool"] == "done"

def test_parse_tool_calls_block():
    text = "TOOL write path=solution.py\nprint('hi')\nEND_TOOL\nDONE"
    calls = parse_tool_calls(text)
    assert calls[0]["tool"] == "write"
    assert calls[0]["content"] == "print('hi')"

def test_parse_tool_calls_skills():
    calls = parse_tool_calls("SKILLS: sandbox-builder, sqli-tester, json-repair-tool\nDONE")
    assert calls[0]["tool"] == "skills"
    assert "sandbox-builder" in calls[0]["chosen"]

def test_skill_pool_20_pick_5():
    assert len(SKILL_POOL) == 20
    names = {s["name"] for s in SKILL_POOL}
    assert "sandbox-builder" in names
    assert "payload-obfuscator" in names
    # validate competitive draft: each agent picks 5
    assert all(s["elo"] == 1200 for s in SKILL_POOL)

def test_tool_session_reject_dotdot(tmp_path):
    sess = ToolSession(tmp_path / "work")
    try:
        sess._resolve("../../etc/passwd")
        assert False
    except ValueError as e:
        assert ".." in str(e) or "escape" in str(e).lower()

def test_tool_session_write_read(tmp_path):
    sess = ToolSession(tmp_path / "work")
    res = sess.write("solution.py", "print('hi')")
    assert "WROTE" in res
    content = sess.read("solution.py")
    assert "hi" in content

def test_tool_session_run_timeout(tmp_path):
    sess = ToolSession(tmp_path / "work", tool_timeout=1)
    sess.write("loop.py", "while True: pass")
    out = sess.run("loop.py")
    assert "timeout" in out.lower()

def test_advanced_executor_requires_sandbox_gate():
    import os
    from agent_arena.sandbox.executors.advanced_executor import AdvancedExecutor
    os.environ.pop("ARENA_IN_SANDBOX", None)
    ex = AdvancedExecutor()
    try:
        ex.run_battle(battle_id="b", format_config={"name":"Tool-using coding race","engine":"agent_tool_race","roles":["player_a","player_b","judge"],"phases":[{"name":"race","participants":["player_a","player_b"]}],"target_code":"x","max_tool_turns":1}, model_ids=["a","b"], round_visibility="open", timeout_seconds=60, role_to_model={"player_a":"a","player_b":"b"}, client=None)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "sandbox" in str(e).lower()

def test_get_executor_resolves_advanced():
    from agent_arena.sandbox.executors import get_executor
    from agent_arena.sandbox.executors.advanced_executor import AdvancedExecutor
    cfg = {"name": "Tool-using coding race", "engine": "agent_tool_race"}
    assert isinstance(get_executor(cfg), AdvancedExecutor)
    cfg2 = {"id": "tool-using-coding-race", "engine": "agent_tool_race"}
    assert isinstance(get_executor(cfg2), AdvancedExecutor)
