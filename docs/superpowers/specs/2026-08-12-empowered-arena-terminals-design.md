# Empowered Arena Terminals — Design

Date: 2026-08-12
Status: Approved for implementation
Branch: `main` (single branch; env-driven config)

## Goal

Transform the arena into **one universal agent loop**: every battle format gives every participant the full toolbelt (shell, filesystem++, web, install, skills, process manager, streaming `action_log`), a live per-fighter preview pane, an arena-owned skill library with persistent Elo + memory, and a synthetic cyber + web-app targets library — proven first on a vertical slice (tool-race format), then migrated to all formats as data.

## Safety boundary (non-negotiable)

All offensive-security behavior executes only against synthetic targets inside disposable Modal sandboxes:

- intentionally vulnerable fixtures, localhost services, generated credentials, synthetic datasets, challenge-owned resources
- never: scanning arbitrary Internet hosts, real credentials, real systems, persistence, exfiltration, registry modification, C2
- secrets are fake (`FLAG{...}`), egress limited to sandbox preview/workdir
- difficulty changes simulation parameters — never containment

## Architecture decisions (locked)

1. **One engine, formats = data.** `AdvancedExecutor` becomes the universal orchestrator. Format config (roles/phases/target/rubric/weights/difficulty/scoring/artifacts/recommended_skills) is pure data. Legacy single-phase executors retire after all formats verified on the engine.
2. **Universal toolbelt** (all seven capabilities in the same agent loop):
   - `SHELL` — real bash (timeout + killpg, output cap)
   - Filesystem++ — `GREP`, `TREE`, `CP`, `MV`, `RM` (plus existing `WRITE`/`READ`/`LS`/`CLEAN`)
   - Web — `FETCH` (httpx), `SEARCH` (defaults to a note + suggestion to FETCH; no external search key)
   - Install — `INSTALL` (pip/apt/npm via bash, streamed logs)
   - Skills — `SKILLS` (list), `USE_SKILL` (load SKILL.md body into context)
   - Process manager — `BG`/`PS`/`KILL`/`LOGS` (ring-buffer reader threads)
   - Streaming execution events — every tool call emitted as `action_log` event (not `artifact`)
3. **Live preview (Sandpack feel).** Sandbox spawned with `encrypted_ports=[8080,8081]`; each participant's workdir is served by a static preview server (`python -m http.server`) on its assigned port; URLs published to the battle doc + `preview` SSE event `{model_id, url}`; frontend iframe hot-reloads (key-bump) on `artifact`/`action_log` events. v1 = static serve; vite HMR is follow-up. **Decision (2026-08-12): stay on Modal tunnels + static preview — live sandbox fidelity required (Python/cyber artifacts, agents can `bg` servers). Sandpack (browser-only JS/TS renderer) and codesandbox-sdk were evaluated and deferred as future options; not adopted now.**
4. **Full dev-env image.** python3.11 + node/npm + git + curl + build-essential + ripgrep + tree + jq. Skills mounted at `/opt/arena-skills`.
5. **Full-trust inside sandbox; Appwrite is the only ceiling.** No path/tool/output caps inside the sandbox. `redact.py` artifact cap raised from 100KB to a configurable Appwrite-safe bound (~1MB, truncation marker).
6. **Skill system.** Richer frontmatter (name, description, version, tier, category, tags, prerequisites, capabilities, allowed_environments). Loader/validator: `load_skill`, `list_skills`, `filter_skills`, `validate_skill` (explicit errors), `resolve_prerequisites`. Runtime metrics (elo/wins/losses/draws/uses/success_rate) live in a persistent Appwrite `skills` collection, updated deterministically after validated outcomes with decay. Agent gets a ranked 2–3 skill shortlist + loads only selected SKILL.md bodies (progressive disclosure).
7. **Skill library (arena-owned).** Seed 5 cyber skills — `payload-obfuscator`, `sandbox-builder`, `credential-hunter`, `waf-rule-generator`, `polyglot-escape` — plus user-curated picks. Each SKILL.md follows the required doc format; **drafted for user review, not go-live until approved**.
8. **Targets library.** `targets/` YAML per format: TARGET.md brief, tests, README, optional example code, reference URLs. Random pick per battle. Seed cyber targets first; web-app seeds decided later.
9. **Memory.** Self-hosted Appwrite `memories` collection (replaces dormant mem0 push): after each run store challenge type, difficulty, skills selected, combination, outcome, score, failure reason, strategy summary, duration. Retrieval pulls only relevant past results into agent context. No raw transcripts injected.
10. **Difficulty + novelty.** novice/intermediate/advanced/expert alters variables/info/decoy/time/hints — never containment. Novelty fingerprint (category, skills, tool sequence, result) → unseen+successful = bonus.
11. **Campaigns: deferred (stretch).** Multi-stage directed graphs come after the single-challenge arena is stable.

## Implementation order (single `main` branch)

| #   | Work                                                | Files                                                                                                      |
| --- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| A1  | Toolbelt upgrade + `action_log` streaming           | `advanced_executor.py`, `_harness.py`                                                                      |
| A2  | Full dev image + `encrypted_ports`                  | `sandbox_launcher.py`                                                                                      |
| A3  | Preview servers + `preview` event + URL persistence | new `executors/preview.py`, `executors/procs.py`, `sandbox_launcher.py`, `internal_router.py`, `client.py` |
| A4  | Frontend preview iframes + file-tree                | `LiveBattle.tsx`, `CodePane.tsx` (already parses `action_log` + file-tree)                                 |
| A5  | Caps raise                                          | `redact.py`                                                                                                |
| B6  | Format manifest extension                           | `seed_formats.py`                                                                                          |
| B7  | Migrate formats to universal engine                 | `executors/__init__.py`, `seed_formats.py`                                                                 |
| C8  | Skill loader/validator                              | `skill_pool.py` (extend)                                                                                   |
| C9  | Appwrite `skills` registry + decay                  | new `skills_registry.py`, `db.py`                                                                          |
| C10 | Selection protocol                                  | `advanced_executor.py`                                                                                     |
| D11 | Targets library + cyber seeds                       | `targets/`, `seed_targets.py`                                                                              |
| D12 | Draft 5 cyber skills (review)                       | `.kilo/skills/<5>`                                                                                         |
| D13 | Appwrite `memories` + retrieval                     | new `memory.py`                                                                                            |
| E14 | Difficulty                                          | `seed_formats.py`, engine                                                                                  |
| E15 | Novelty                                             | engine                                                                                                     |
| F17 | Tests                                               | `backend/tests/`                                                                                           |
| F18 | Deploy + E2E verify                                 | modal + Vercel + `/stats`                                                                                  |

## Success criteria

- One live battle on the universal engine: agent uses SHELL/INSTALL/FETCH + skills → multi-file solution → preview URL streams into frontend iframe → `action_log` shows tool calls → judge scores → skill Elo persists to Appwrite → target pulled from library.
- Loader gates pass (list/filter/validate/prereqs); malformed skill = explicit error.
- All 14 formats run on one engine; repo runnable after each phase.
