---
name: advanced-builder
description: Global advanced builder for tool-using executors, full code-execution toolbelts, and competitive battle formats. Builds advanced_executor.py with filesystem+python exec+test runner, sandbox gate, and wires into Agent Arena. Use when user says 'advanced-builder', '/advanced-builder', 'tool-using coding race', 'give battle agents full tools', 'build advanced_executor', 'omni toolbelt', 'build and break with tools', 'agent_tool_race'. Trigger phrases: advanced-builder, advanced executor, tool-using race, agent_tool_race, full toolbelt, build and break, give agents tools and competition
---

# Advanced Builder - Global

You are the global Advanced Builder. You build maximal-access executors where battle agents get full tools, a task, and competition.

## When to use (trigger-friendly)

- User says: "advanced-builder" or "/advanced-builder" or "@advanced-builder"
- User asks: "give agents code exec and tools", "build tool-using coding race", "build advanced_executor.py"
- User mentions: "agent_tool_race", "omni toolbelt", "build & break with tool loops", "give battle agents full filesystem + python + test runner"
- User wants: Frontend Code (WRITE frontend/src, pnpm build, Playwright screenshot), Appwrite DB Write, Self-Evolve levels

**Examples:**
1. User: "Build me an executor where agents can read/write/ls/run python and test" -> load this skill
2. User: "I want tool-using coding race with sandbox gate" -> load this skill
3. User: "Create advanced_executor.py per spec with ARENA_IN_SANDBOX gate" -> load this skill

## Core workflow (progressive disclosure, additive-only)

**Step 0 - Load order (read first):**
`base.py` -> `client.py` -> `executors/__init__.py` -> `build_and_break.py` -> `agent_vs_agent.py` -> `formats/__init__.py` -> `entrypoint.py` -> `seed_formats.py` -> `conftest.py + tests` -> `redact.py`
See `references/` for condensed refs: base_executor_reference.md, client_reference.md, build_and_break_reference.md, seed_formats_reference.md, entrypoint_reference.md, redact_policy.md

**Step 1 - Create executor:**
Use `scripts/` for deterministic logic - never put business logic in SKILL.md.
- `scripts/parse_tool_calls.py` - strict sequential parser: single-line TOOL read/ls/test/clean and block TOOL write/run ... END_TOOL, DONE ends turn
- `scripts/tool_session.py` - ToolSession under `arena-tools-` root, _resolve rejects "..", Popen(start_new_session=True)+killpg 15s timeout, 50KB cap
- `scripts/validate_sandbox_gate.py` - validates hard gate ARENA_IN_SANDBOX==1 at top of run_phase
- `scripts/generate_advanced_executor.py` + `scripts/patch_seed_formats.py` - generation helpers

**Step 2 - Wire:**
- `formats/advanced.py` from `assets/advanced.py.template` -> registers "Tool-using coding race" / "tool-using-coding-race"
- Modify `formats/__init__.py` append: `from . import advanced as _advanced` (see assets/entrypoint_patch.py)
- Modify `sandbox/entrypoint.py` set flag: `os.environ["ARENA_IN_SANDBOX"]="1"`
- Modify `seed_formats.py` additive-only new engine `agent_tool_race` with roles player_a/b/judge, rubric, definition, extra with is_palindrome kata (use assets/format_extra_template.json, assets/target_code_kata.py)

**Step 3 - Templates (assets/):**
- `assets/advanced_executor.py.template` - full executor skeleton
- `assets/advanced.py.template` - format registration
- `assets/format_extra_template.json` - FORMAT_EXTRA sample
- `assets/target_code_kata.py` - is_palindrome kata with TEST_PASS/TEST_FAIL
- `assets/entrypoint_patch.py` - entrypoint patch

**Step 4 - Verification:**
`cd backend && pytest tests/test_advanced_executor.py -q` no regression. See `tests/test_cases.md` and `expected_outputs/`

## Tool protocol (see resources/tool_protocol.md for operational, references for background)

Single-line:
  TOOL read path=<rel>
  TOOL ls [path=<rel>]
  TOOL test path=<rel>
  TOOL clean path=<rel>
Block:
  TOOL write path=<rel>
  <content>
  END_TOOL
  TOOL run [path=<rel>]
  <python>
  END_TOOL
DONE ends turn.

Parser strict sequential line scan, unknown tool -> error string, don't crash.

## Safety - Always/Never (see resources/business_rules.md)

**Always:**
- Always use `sanitize_artifact()` via redact.py for every artifact before client.round
- Always reject ".." in _resolve - raise ValueError -> "ERROR: ..."
- Always use Popen with start_new_session=True + killpg SIGKILL on timeout 15s
- Always cap output 50KB with [TRUNCATED]
- Always gate at top of run_phase: if ARENA_IN_SANDBOX != "1" raise RuntimeError
- Always load scripts/ for exec logic, resources/ for operational knowledge, references/ for deep background, assets/ for templates, examples/ for samples

**Never:**
- Never modify existing executors (same_target_race.py, build_and_break.py, scripted.py, etc) - additive-only
- Never edit existing format definitions in seed_formats.py - only append Tool-using coding race
- Never provide in-process fallback for run - must be subprocess
- Never put business logic in SKILL.md - delegate to scripts/
- Never log secrets or PII

## Progressive disclosure

- Start with this SKILL.md only (concise guide)
- Need validation/exec logic? Load `scripts/parse_tool_calls.py`, `tool_session.py`, `validate_sandbox_gate.py`
- Need engine/rubric shape? Load `resources/engine_template.json`, `resources/rubric.md`, `resources/tool_protocol.md`, `resources/business_rules.md`, `resources/next_gen.md`
- Need templates? Load `assets/`
- Need deep background? Load `references/`
- Need samples? Load `examples/sample_tool_write.md`, `sample_tool_run.md`, `sample_done_final.md`, `executor_result.json`
- Need validation? Load `tests/` + `evals/` - see evals/README.md

## Resources vs References vs Assets (per enterprise structure)

- `resources/` = Operational files the agent uses during task: tool_protocol.md, business_rules.md, engine_template.json, rubric.md, next_gen.md, data_schema.json (if any) - directly shapes execution
- `references/` = Longer background documents: SOPs, base executor, client, build_and_break, entrypoint, seed_formats, redact_policy - consult only
- `assets/` = Static files used in output creation: templates, entrypoint patch, kata, format_extra - supports final output
- `scripts/` = Executable task logic: deterministic Python
- `examples/` = Sample inputs/outputs, before/after, edge cases, bad examples
- `tests/` = Test cases, expected outputs, failure modes
- `evals/` = Optional validation cases for security/regression (new per import guide)

## Outputs

- `backend/agent_arena/sandbox/executors/advanced_executor.py`
- `backend/agent_arena/sandbox/executors/formats/advanced.py`
- Patch to `formats/__init__.py`, `entrypoint.py`, `seed_formats.py`
- `backend/tests/test_advanced_executor.py` covering parser, ToolSession happy + .. rejection, run timeout kills pg, gate, full loop FakeTransport, registry

## Validation checklist (from import guide)

- [ ] Folder name `advanced-builder` matches frontmatter `name: advanced-builder`
- [ ] Description trigger-friendly with example user phrases (see top)
- [ ] Instructions explicit with always/never + 2-3 examples
- [ ] SKILL.md concise (<150 lines guide, deeper in subfolders)
- [ ] Tested locally in new agent session
- [ ] `cd backend && pytest tests/test_advanced_executor.py tests/test_sandbox_runner.py tests/test_executor_registry.py -q` passes

## Next-gen idea bank (DO NOT IMPLEMENT unless asked - see resources/next_gen.md)

- Frontend code: WRITE frontend/src, pnpm build, Playwright screenshot
- Appwrite DB write: DB_CREATE/READ scoped by battle_id
- Self-evolve: WRITE executors/formats/*.py, pytest, AST validation, human review queue
