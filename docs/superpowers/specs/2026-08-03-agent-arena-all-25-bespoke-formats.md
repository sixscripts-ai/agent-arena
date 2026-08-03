# Agent Arena — Plan 3: All 25 Formats Fully Bespoke (Design Spec)

Date: 2026-08-03

## 1. Overview

Plan 2 shipped 6 real sandbox formats (3, 6, 7, 9, 10, 12) plus a scripted
fallback for the other 19. This plan makes **all 25 formats fully bespoke**: every
format gets its own executor module with real code execution in the Modal
Sandbox, a curated static target, and a machine-readable win outcome.

Decisions locked with the product owner:

1. **Batch by engine family** — build, test, deploy one family at a time
   (A → B → C → D → E).
2. **One executor module per format** — dispatched by format slug, fallback to
   the existing engine executor for any format not yet migrated.
3. **Explicit outcome markers** — each executor detects a structured outcome and
   emits a machine-readable `EXECUTOR_RESULT` line + `event_type="result"`.
4. **Curated static targets** — targets, assets, hidden tests, and harness
   parameters live in each format's config in `seed_formats.py`. Identical
   inputs for both sides.

## 2. Scope

- New `backend/agent_arena/sandbox/executors/formats/` package: one `Executor`
  subclass per format, each overriding `run_battle()` to manage its own
  workdir/service lifecycle, turn ordering, and cross-phase state.
- Dispatch via `get_executor(format_config)`: lookup by format slug; fallback to
  today's `get_executor(engine)`. Existing 16 formats keep working throughout.
- Each executor ends by appending `EXECUTOR_RESULT: <json>` to the final
  artifact and publishing an `event_type="result"` event with parsed JSON.
- Curated targets embedded in each format's config JSON in `seed_formats.py`.
- Hermetic pytest per format (FakeTransport model replies, real local Python on
  a temp dir) plus one real harness smoke test per format.
- Deferred: frontend win-badge switch to parsed `result` events (done after
  Batch A is verified live); seed/format copy polish.

## 3. Architecture

```
               Modal backend (FastAPI)
                 │  POST /internal/model ◄────┐
                 │  POST /internal/judge ◄────┼── X-Internal-Key
                 │  POST /internal/round ◄────┤   per-battle validation
                 └───────────▲────────────────┼──────────────┘
                             │ spawn (sandbox_id tracked)
                 ┌───────────┴─────────────────┴────────────┐
                 │  Modal Sandbox — battle runner            │
                 │  runner.py → get_executor(format_config)  │
                 │    ├─ bespoke executor → run_battle()     │
                 │    └─ engine executor → phase loop         │
                 │  executors/formats/<slug>.py (25 modules) │
                 │  client.py (internal API client)          │
                 └───────────────────────────────────────────┘
```

- `runner.run_battle_loop` checks the executor: if the resolved executor has a
  `run_battle` override, it calls it once (skipping the generic phase loop);
  otherwise it runs the existing phase loop with `run_phase`.
- The `base.Executor` gains a default `run_battle` that simply runs the phase
  loop via `run_phase` — so the two paths share one entry point.
- Persisted workdir + service lifecycle live inside `run_battle` for bespoke
  formats, so multi-phase formats (Arms race, Exploit vs patch, Digital twin,
  Adaptive attacks, Time-limited siege) share state across rounds.
- All artifacts/rounds still flow through `client.round(...)`; keys never enter
  the sandbox.

## 4. Components

### 4.1 Format executor package

```
executors/formats/
  __init__.py          # FORMAT_EXECUTORS: {slug: ExecutorClass}
  waf_vs_bypasser.py   # format 1
  auth_vs_breaker.py   # format 2
  sandbox_vs_escapee.py# format 3 (exists as build_and_break; moved, kept)
  rev_shell_vs_defense.py      # 4
  payload_vs_detection.py      # 5
  code_review_duel.py          # 6 (moved from same_target_race)
  debugging_race.py            # 7
  re_solve_race.py             # 8
  prompt_injection_vs_hygiene.py # 9 (moved from direct_duel)
  jailbreak_vs_guardrail.py    # 10
  arms_race.py                 # 11
  two_agent_duel.py            # 12 (moved from agent_vs_agent)
  pwn_exploit_race.py          # 13
  credential_hunt.py           # 14
  lock_vs_pick.py              # 15
  polymorph_vs_signature.py    # 16
  cred_reuse_vs_hardening.py   # 17
  detection_cat_and_mouse.py   # 18
  exploit_vs_patch.py          # 19
  time_limited_siege.py        # 20
  digital_twin.py              # 21
  tool_abuse_vs_enforcement.py # 22
  attacker_vs_guardrails.py    # 23
  injection_vs_hardened.py     # 24
  same_defense_adaptive.py     # 25
```

- Each module exports `class <Name>Executor(Executor)` with a single
  `run_battle(...)` override returning `list[dict]` artifacts.
- `__init__.py` registry maps slug → class. Slug = the format id from
  `seed_formats.py` (e.g. `waf-builder-vs-bypasser`).
- `get_executor(format_config)` (in `executors/__init__.py`) resolves slug first,
  falls back to engine.

### 4.2 Outcome convention

- Every bespoke executor appends a final line to the last artifact:
  ```
  EXECUTOR_RESULT: {"builder": "BLOCKED", "breaker": "BYPASSED", "attempts": 12}
  ```
- The executor also calls `client.round(battle_id, phase, "system",
  json.dumps(result), event_type="result")` so the parsed outcome is a first-class
  SSE event. Per-round results are published as they happen for multi-round
  formats.
- Markers are lowercase-normalized and validated against the format's declared
  `outcome_markers` in config. Unknown/empty result → executor treats the round
  as inconclusive and reports it, never fabricating a win.

### 4.3 Curated targets in seed config

`seed_formats.py` `FORMAT_DEFINITIONS` gains an optional per-format `extra`
dict merged into the built config:

```python
FORMAT_EXTRA = {
  "code-review-duel": {
    "target": {"code": "…vulnerable snippet…", "tests": ["assert …"]},
    "exec_timeout_seconds": 120,
  },
  ...
}
```

Standard keys: `target` (assets per format), `outcome_markers` (list),
`exec_timeout_seconds`, `duel_turns`, `max_attempts`, `layers`, `time_budget_s`.
`build_format` merges `extra` into the config JSON. Re-seed is idempotent
(upsert by name) and updates deployed Appwrite docs. No schema change — all data
rides the existing `config` string.

### 4.4 Harness style

- Inner code runs under the same openness as format 3 today: network egress on,
  real fs under the battle workdir, subprocess allowed, inner-exec timeout
  (`exec_timeout_seconds`, default 180) enforced by a watchdog.
- Harnesses (TCP listener, flag file, login stub, detection runner) are owned by
  the executor, not the models — deterministic and testable.
- Curated targets live in config; the executor writes them to the workdir before
  phases run.

## 5. Batch A format specs (Group A: script_vs_defense ×4 + high_complexity ×5)

| # | Format | What executes | Outcome markers |
|---|---|---|---|
| 4 | Reverse shell vs network defense | Defender writes a firewall rule-set JSON; attacker writes a shell that connects to the harness C2 port; executor applies the rule-set, attempts the connect, checks echo | `SHELL_ESTABLISHED` / `SHELL_BLOCKED`; defender `DEFENDER_DETECTED`/`DEFENDER_MISSED` |
| 5 | Payload generator vs detection | Attacker transforms curated base payloads into variants; defender classifies each; executor computes detection + false-positive rate over a benign baseline | `EVADED_ALL` / `DETECTION_RATE_<pct>` / `FALSE_POSITIVES_<n>` |
| 16 | Polymorphic script vs signature defense | Attacker mutates a base script into N variants; defender detects variants + benign samples; executor runs both | `POLYMORPH_EVASION_RATE` |
| 17 | Credential-reuse script vs hardening | Defender writes a hardened login service (lockout/rate-limit/MFA); attacker stuffs a curated cred list at it | `COMPROMISED` / `LOCKED_OUT`; defender `ATTACK_BLOCKED` |
| 11 | Arms race | 4–6 escalating attack→defend rounds on a curated target service; per-round pass/fail; both sides see history | `ATTACK_SUCCEEDED`/`ATTACK_BLOCKED` per round + final tally |
| 19 | Exploit vs patch | Exploit the curated vulnerable service to read the flag; apply defender's patch; re-run exploit | `EXPLOITED` / `PATCHED` (before/after) |
| 20 | Time-limited siege | Both sides attack a multi-layer target under a strict per-layer time budget; count layers breached | `LAYERS_BREACHED_<n>` |
| 21 | Digital twin | Attacker acts against a realistic twin service while defender monitors concurrently; count impact vs detections | `IMPACT_<n>` / `DETECTED_<n>` |
| 25 | Same-defense adaptive attacks | Both players run 3 adaptive rounds against one fixed defense; each round sees prior successes before acting | per-round `SUCCESS`/`FAIL` |

Detailed per-format behavior is captured in each executor module + its config
`extra` (exact target JSON, harness script, marker set, tuning). Written during
implementation, verified by the format's hermetic test.

## 6. Testing

- **Hermetic suite (default):** `pytest tests/` — one test file per format
  executor. `FakeTransport` supplies model replies; the executor runs under real
  local Python against a temp workdir; asserts exact `EXECUTOR_RESULT` JSON,
  marker strings, round ordering, and `event_type="result"` publication.
- **Harness smoke (default):** one real (non-mocked) test per format verifies the
  harness itself (e.g. #4 TCP connect/block, #19 flag read, #5 detection math)
  with scripted inputs, no Modal.
- **Registry/dispatch test:** `get_executor` resolves slug → bespoke class and
  falls back to engine for unmigrated slugs.
- Run with `backend/.venv/bin/python -m pytest` from `backend/`.

## 7. Rollout

Per batch: seed (`ARENA_*` seed re-run) → `pytest` green → `modal deploy
modal_entry.py` → live smoke battle per format via API → next batch.

The slug→executor registry with engine fallback keeps the 16 unmigrated formats
working until each batch lands, so any batch can ship independently.

Batch order: A (script_vs_defense + high_complexity) → B (build_and_break) →
C (same_target_race) → D (direct_duel) → E (agent_vs_agent).

## 8. Out of scope (deferred)

- Frontend win-badge switch from string-scan to parsed `result` events (small,
  after Batch A verified live).
- New format creation or copy polish beyond the existing 25.
- Anything requiring non-Python runtimes (C/go binaries) — keep targets
  Python-runnable so the sandbox base image stays unchanged.
