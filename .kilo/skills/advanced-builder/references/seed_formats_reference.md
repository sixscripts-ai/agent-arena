# Seed Formats Reference

From backend/agent_arena/seed_formats.py

- ENGINE_TEMPLATES dict: build_and_break, script_vs_defense, same_target_race, direct_duel, high_complexity, agent_vs_agent
- New to add: agent_tool_race roles player_a/b/judge, phases race participants player_a/b, judge participants judge inputs race, weights race 1.0
- RUBRICS dict: per engine
- FORMAT_DEFINITIONS list of tuples (name, engine, description) - 25 existing, append 26th Tool-using coding race
- FORMAT_EXTRA dict per format name: exec_timeout, outcome_markers etc
- New extra: Tool-using coding race target_code is buggy is_palindrome with asserts, max_tool_turns 6, max_tool_steps 14, tool_timeout 20, exec_timeout 240, markers DONE/TEST_PASS/TEST_FAIL/STEP_BUDGET_EXCEEDED
- _slugify truncates to 36 chars, build_format uses template + extra
- seed_formats() upserts via appwrite
- Additive-only: do not modify existing entries
