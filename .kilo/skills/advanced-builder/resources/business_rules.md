# Business Rules - Additive Only

- Do NOT modify existing executors: same_target_race.py, build_and_break.py, scripted.py, direct_duel.py, agent_vs_agent.py
- Do NOT modify existing format definitions in seed_formats.py, only append new: Tool-using coding race
- Do NOT touch frontend
- Every artifact via sanitize_artifact() before client.round
- Style: __future__ import annotations, type hints, short docstrings, no new external deps
- Sandbox gate non-negotiable at top of run_phase(): if ARENA_IN_SANDBOX != "1" raise RuntimeError
- ToolSession workdir under shared TemporaryDirectory root prefix "arena-tools-"
- Write/read/ls/clean resolve against workdir, REJECT ".." escapes
- run uses Popen(["python3", path], cwd=workdir, env ARENA_ROOT+ARENA_WORKDIR, start_new_session=True), killpg on timeout, 50KB cap
- Tests must follow conftest.py conventions, use FakeTransport
