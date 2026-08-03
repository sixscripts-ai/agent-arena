# Tool-using coding race — 20 skills pool, pick 5 per battle
Date: 2026-08-03
Status: approved (brainstorming B for now)
Owner: villain
Branch: feat/all-25-bespoke-formats (14/3 archival done, PR #1)

## Overview
Current battles produce single-file `BUILD_CODE:\n---STDOUT---` dumps (build_and_break executor). Looks copy-paste, no purpose, no reusable asset. User wants high-level output with file tree + purposeful coding that produces usable tools/skills, plus skill-based agents that choose 3-5 of 20 available skills per battle to develop technique/theory, with self-learning from each battle via mem0 + Elo.

This spec introduces `agent_tool_race` engine (from .kilo/skills/advanced-builder) where agents get full toolbelt (filesystem + python exec + test runner), 20 skills pool dynamic from existing .kilo/skills/ + custom_skills/, pick 5 each battle, must document THEORY.md, produce workspace snapshot {solution.py, THEORY.md, tests/, EXECUTOR_RESULT.json} that becomes reusable skill/tool.

## Goals
- Fix copy-paste look: CodePane shows file tree work/ ├─ sandbox.py ● BUILDER ├─ escape.py ● BREAKER ├─ policy.json + badges SANDBOX_READY, tok/s, TEST_PASS, WIN, not raw BUILD_CODE dump
- Purposeful coding: battles produce usable asset (e.g., WAF ruleset rules.json, detection detect.py, hardening policy.json, code fixer solution.py) that can be deployed or promoted to .kilo/skills/
- Skill-based agents: 20 total skills curator-chosen by user from existing skills, agent must choose exactly 5 per battle via SKILLS: line + read SKILL.md via TOOL read
- Technique/theory: require THEORY.md explaining why 5 chosen, e.g., "sandbox-builder + sqli-tester + json-repair = defense-in-depth"
- Self-learning: mem0 villain/sixscripts-ai-agent-arena stores winning chosen 5 + theory snippet as few-shot for next battle; Elo registry for skills: winning 5 +5, losing -5, prune <1000, keep >1300 via existing leaderboard.py
- No GPU training for now (B not C): B for now, C (SFT on 100+ tool traces → host:arena-tuned) later after 100 battles

## Non-goals
- Not training a model now (C later)
- Not changing 14/3 archival (WAF, Auth, Code sandbox, Arms race etc stay)
- Not rewriting all executors, only adding agent_tool_race additive
- Not committing .kilo/ runtime (node_modules, memory.json) — only kilo.json + agents

## Architecture

### Backend — new engine agent_tool_race
- Engine template: roles [player_a, player_b, judge], phases [race(player_a,player_b) → judge], weights race 1.0. Exists in .kilo/skills/advanced-builder/resources/engine_template.json
- Rubric: "Judge correctness vs TARGET.md, test coverage, efficiency, workspace state 0-100" from resources/rubric.md
- Format definition additive: ("Tool-using coding race","agent_tool_race","Fix shared TARGET via toolbelt competition")
- Format extra: from assets/format_extra_template.json target_code is_palindrome kata (buggy case-sensitive, ignore non-alnum), max_tool_turns 6, max_tool_steps 14, tool_timeout 20, exec_timeout 240, outcome_markers [DONE,TEST_PASS,TEST_FAIL,STEP_BUDGET_EXCEEDED]
- Registry: formats/__init__.py add from . import advanced as _advanced (was removed in archival, re-add)

### Executor advanced_executor.py
- Location backend/agent_arena/sandbox/executors/advanced_executor.py from assets/advanced_executor.py.template + scripts/generate_advanced_executor.py
- Must have sandbox gate at top of run_phase: if ARENA_IN_SANDBOX != "1": raise RuntimeError("must run inside sandbox")
- entrypoint.py patch: os.environ["ARENA_IN_SANDBOX"]="1" before client creation per references/entrypoint_reference.md
- Toolbelt parser parse_tool_calls.py: strict sequential line scan, single-line TOOL read path=<rel> / ls [path=<rel>] / test path=<rel> / clean path=<rel>, block TOOL write/run path=<rel> … END_TOOL, DONE ends turn, unknown → ERROR no crash
- ToolSession tool_session.py: TemporaryDirectory arena-tools-, _resolve rejects .. and absolute escape, write/read/ls/clean against workdir, run via Popen(start_new_session=True) + killpg SIGKILL 20s timeout, 50KB cap + [TRUNCATED], env ARENA_ROOT/ARENA_WORKDIR, test parses TEST_PASS/TEST_FAIL + rc
- Validation: validate_sandbox_gate.py must gate, business_rules.md additive-only, always sanitize_artifact before client.round, reject ..

### Frontend — file tree (B awesome card)
- LiveBattle.tsx already refined 439 lines deployed frontend-lipxnoib3 → agent-arena-blond: copy id, logFilter all/build/break/judge, logAutoScroll, phaseSteps with blurb, event stream terminal 240px fixed, uuid deduped
- CodePane.tsx current: props code: string monolithic, split("\n") line numbers capped 80, pre whitespace-pre-wrap break-all, artifactMeta kb + lines + win badge
- Upgrade: parse structured artifact if executor emits {files:{path:content}, stdout, stderr, tests_passed, chosen_skills, theory, steps_used}. Left tree: work/ files with badges ● BUILDER ● BREAKER TEST_PASS. Right viewer tabs per file. Keep backwards compat: if artifact is string (old executors), show as before
- New: chosen_skills chips + THEORY.md viewer tab in LiveBattle

### Self-learning loop
- mem0: POST https://api.mem0.ai/v1/memories/ user_id villain, Authorization Token m0-... (already shared via ~/.zshrc + mcp.json). After win, store {"chosen_skills": [...5], "theory": THEORY.md snippet, "format": format_id, "elo_delta": ...} metadata project agent-arena
- Next battle: _load winning memos via search, inject top-3 past winning combos as few-shot into system prompt for player_a/b: "Past winning 5-skill combos: [sandbox-builder, ...] theory: ..."
- Elo registry: reuse leaderboard.py apply_result logic for skill Elo. New collection or reuse leaderboard with model_id = skill name, format_id = overall-skills. winning 5 +5, losing -5, games_played++. Prune <1000, keep >1300. Agents see current skill Elo in system prompt: list 20 skills with elo + description
- Technique/theory: THEORY.md required in workspace, must explain why 5 chosen. Judge rubric adds skill composition + theory quality

### Data flow
1. POST /battles format_id tool-using-coding-race model_ids [host:groq-llama, host:tokenrouter] (host free, no BYOK) arena_size 2 timeout 300 visibility open save True
2. sandbox_launcher.start_battle → run_in_process direct (ARENA_INPROCESS_DIRECT=1) → _load_battle cfg from formats collection
3. get_executor resolves AdvancedExecutor via FORMAT_EXECUTORS name "Tool-using coding race"
4. AdvancedExecutor.run_battle: for each turn up to 6, model via client.model (host:groq-llama uses HOST_GROQ_KEY, host:tokenrouter uses HOST_TOKENROUTER_KEY kimi-k3-free), parses TOOL lines, ToolSession executes, client.round emits artifact + action_log + result events with uuid deduped
5. DONE → ls work/ → EXECUTOR_RESULT: {model_id, passed, steps, files, chosen_skills, theory} via emit_result event_type result
6. finish() → judge_battle via host judge (now wk-Royo...ws-wDOT... valid dot Bearer → moonshotai/Kimi-K3) fallback TokenRouter kimi-k3-free → Groq → DeepSeek → OpenRouter, returns scores 0-100 clamped, justifications
7. Scores upserted via leaderboard.py, events durable battle_events, rounds saved if saved=True
8. Frontend streamBattle SSE: durable load then subscribe, filteredArts logFilter, codeA/B = filter model_id join artifact (now files JSON), CodePane file tree, scores display winner + Elo delta

## Skill pool — 20 total, pick 5 each battle (dynamic, you choose)

### Source
- .kilo/skills/*: advanced-builder, arena-quality-gate, arena-security-audit, arena-ui-ux-review, etc
- custom_skills/: json_repair_tool.py, ragas_evaluator.py, etc
- User will curate final 20

### Proposed starter 20 (editable)
1. sandbox-builder
2. polyglot-escape
3. payload-obfuscator
4. waf-rule-generator
5. credential-hunter
6. sqli-tester
7. xss-bypasser
8. json-repair-tool
9. ragas-evaluator
10. playwright-scraper
11. secret-redactor
12. auth-hardener
13. reverse-shell-builder
14. detection-signature
15. exploit-patcher
16. time-siege-cracker
17. digital-twin-attacker
18. adaptive-payload
19. tool-abuse-detector
20. ui-ux-auditor

### Pick 5 rule
System prompt at battle start lists 20 with elo + description. Agent must output SKILLS: a,b,c,d,e + read 5 via TOOL read .kilo/skills/.../SKILL.md + TOOL write solution.py using 5 + TOOL write THEORY.md + TOOL test. Example THEORY: "Chosen sandbox-builder + sqli-tester + json-repair + credential-hunter + playwright-scraper = defense-in-depth: sandbox blocks exec, sqli tests DB, json-repair cleans logs, hunter finds creds, scraper validates XSS in browser"

## Error handling
- Tool .. escape → _resolve rejects, returns ERROR: path outside workdir, no crash
- TOOL unknown → ERROR: ... no crash
- run timeout 20s → killpg SIGKILL, stderr timeout after 20s, rc -1
- TEST_FAIL → artifact saved, judge penalizes coverage, but battle continues
- Judge 429 OpenRouter free-models-per-day → fallback Groq → DeepSeek → OpenRouter (already in judge.py)
- Modal proxy incomplete wk- only → error message guides to generate full wk-....ws-.... dot Bearer via dashboard Settings → Proxy Auth Tokens

## Testing
- tests/test_advanced_executor.py from skill: parser single-line + block + DONE + unknown ERROR, ToolSession .. rejection, run timeout killpg, gate, FakeTransport full loop race + judge, registry get_executor resolves tool-using-coding-race by name and slug
- pytest --ignore=tests/evals → currently 94 passed, expect 100+ after adding advanced tests
- Manual E2E: POST /battles format tool-using-coding-race host:groq-llama + host:tokenrouter, watch file tree grow in new LiveBattle 439 lines, TEST_PASS badge, THEORY.md viewer, scores via Kimi-K3 judge (wk-Royo...ws-wDOT...) or fallback kimi-k3-free

## Rollout
- Phase 1: Implement advanced_executor.py + formats/advanced.py + seed patch + CodePane file-tree parse (this plan)
- Phase 2: User curates 20 skill names from existing .kilo/skills/ + custom_skills/
- Phase 3: Deploy backend modal deploy modal_entry.py → https://...modal.run 14+1 formats (15 with tool-using race), Vercel prod vercel deploy . --prod --project prj_4ixQVsewtM1O8ROKkl2WMPCujK1H → frontend-lipx... → alias agent-arena-blond
- Phase 4: Collect 50 battles → mem0 has 50 winning combos → agents start with top-3 few-shot → Elo pruning visible as technique/theory evolution

## Open questions
- Should chosen_skills Elo share same leaderboard collection or new skill-leaderboard collection?
- Should THEORY.md be required to pass TEST_PASS or optional bonus?
- Should file tree show all work/ files or only solution.py + THEORY.md + tests/?

## References
- .kilo/skills/advanced-builder/SKILL.md 126 lines
- Assets: advanced.py.template, advanced_executor.py.template, target_code_kata.py, format_extra_template.json, entrypoint_patch.py
- Scripts: parse_tool_calls.py, tool_session.py, validate_sandbox_gate.py, generate_advanced_executor.py, patch_seed_formats.py
- References: base_executor_reference.md, client_reference.md, build_and_break_reference.md, seed_formats_reference.md, entrypoint_reference.md, redact_policy.md
- CodePane.tsx L20-65, LiveBattle.tsx 439 lines refined, api.ts BASE, event_bus.py publish/subscribe uuid deduped
- Battle example 6a70d52a7dab6ef26c0a builder BUILD_CODE Sandbox class, breaker ESCAPE_CODE analysis prose SyntaxError, judge scores 60/12 real Kimi-K3 reasoning
- Battle example 6a70d6a2f331de1c8e07 builder groq-llama 82 vs tokenrouter 8, judge reasoning about __subclasses__ traversal
