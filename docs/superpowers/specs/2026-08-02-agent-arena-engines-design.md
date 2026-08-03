# Agent Arena — Plan 2: Sandbox Engines + Real Judge (Design Spec)

Date: 2026-08-02

## 1. Overview

Plan 1 (backend core) is complete: providers, formats, battles, mock runner, SSE,
Elo leaderboard, Modal deployment — all live. Plan 2 replaces the mock runner with
real sandbox-executed battles and a real host-owned Kimi-K3 judge, and closes the
contract gaps the whole-branch review flagged:

1. **model↔provider linkage** — battle `model_ids` are arbitrary strings with no
   link to the `providers` collection.
2. **Cross-replica SSE** — the in-process `event_bus` loses events across Modal
   containers (scale-to-zero, multiple replicas).
3. **Real judging** — replace deterministic mock scores with a real LLM judge.

## 2. Scope

- Real sandbox battle runner: 6 formats fully implemented across 4 engine types
  (formats 3, 6, 7, 9, 10, 12); remaining 19 formats runnable via a scripted
  fallback executor.
- Real judge (host-owned Kimi-K3 default, per-battle override).
- Provider layer gains `model_name`; battle `model_ids` validated against the
  user's own provider docs **or** the built-in host free provider.
- Host free default model (OpenRouter Nemotron free) so users can battle without
  bringing keys; user keys optional.
- SSE fan-out survives replicas/scale-to-zero (Appwrite event log hybrid).
- Cancel/timeout actually kills the sandbox.

## 3. Architecture

```
                ┌────────────────────────────────────────────────┐
                │           Modal backend (FastAPI)              │
                │                                                │
  Appwrite ─────┤  providers (encrypted keys, model_name)        │
                │  battles (sandbox_id, judge_provider_id)       │
                │  battle_events (SSE log, uuid + created_at)    │
                │                                                │
                │  POST /internal/model  ◄────┐                  │
                │  POST /internal/judge  ◄────┼── X-Internal-Key │
                │  POST /internal/round  ◄────┼── per-battle     │
                │                             │   validation     │
                └──────────▲──────────────────┼──────────────────┘
                           │  spawn (Sandbox   │
                           │   id tracked)     │
                ┌──────────┴───────────────────┴───────────┐
                │   Modal Sandbox — battle runner          │
                │   runner.py (phase loop)                 │
                │   executors/ (4 engine types + scripted) │
                │   client.py (internal API client)        │
                └──────────────────────────────────────────┘
```

- **Backend** owns all model API keys (decrypted only here). Sandboxes never see
  keys — they call back via `/internal/*` for model calls, judging, and round
  persistence.
- **Sandbox** drives the battle: reads format config, runs phases, calls
  `/internal/model` per participant, executes engine logic, collects artifacts,
  calls `/internal/judge`, streams every event via `/internal/round`.
- **SSE** merges an Appwrite event log (durable) with the in-process bus (fast).

## 4. Components

### 4.1 Provider layer (model↔provider linkage)

- `providers` collection gains `model_name` (e.g. `"moonshotai/Kimi-K3"`).
- `ProviderCreate`/`ProviderOut` gain `model_name` (required, min_length 1).
- Backend helper `get_model_call_spec(model_id, user_id)` → `(base_url,
  auth_style, api_key, model_name)`, decrypted from the provider doc — **or**
  resolved from the built-in host free provider (see §4.1.1).
- `POST /battles`: every `model_ids` entry must be either:
  - a provider doc owned by the current user, or
  - the built-in host free provider id (`host:openrouter-free`).
  Unknown/foreign ids → 400.
- Keys never logged, never sent to frontend, never enter sandboxes.

#### 4.1.1 Host free default provider

- Built-in provider always available, no user key required:
  - id: `host:openrouter-free`
  - base_url: `https://openrouter.ai/api/v1`
  - model_name: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - auth_style: `bearer`
  - api_key: from env `HOST_OPENROUTER_KEY` (operator-owned; gitignored)
- Listed in `GET /providers` as a synthetic entry (masked key, not in Appwrite).
- Default free; user keys optional. Battles may mix free vs free, free vs user,
  or user vs user. Elo is real whenever the participating model identities differ.
- **Never commit the OpenRouter key.** Rotate if it was ever pasted into chat.

### 4.2 Role → model mapping

- Format configs keep roles including `judge` (no seed rewrite).
- Non-judge roles only: `playable_roles = [r for r in roles if r != "judge"]`.
- **Order-preserving:** `model_ids[i]` maps to `playable_roles[i]`.
- `POST /battles` requires `len(model_ids) == len(playable_roles)` (else 400).
- `arena_size` must match `len(model_ids)`.

### 4.3 Internal callback API (sandbox → backend)

Shared operator key `INTERNAL_API_KEY` in `.env`; injected into the sandbox image
env via Modal Secret. Auth header `X-Internal-Key`.

- `POST /internal/model` — body `{battle_id, model_id, phase, messages}` →
  validates battle exists and status ∈ {queued, running}, and model_id is a
  participant → decrypts/resolves provider key → calls the LLM (OpenAI-compat;
  `modal_proxy` for Modal-proxied Kimi-K3; bearer for OpenRouter/user keys) →
  returns `{content}`. Rate-limit per battle_id.
- `POST /internal/judge` — body `{battle_id, rubric, weights, artifacts}` →
  runs the judge → returns `{scores: {model_id: score}, justifications}`.
- `POST /internal/round` — body `{battle_id, phase, model_id, artifact}` →
  redacts + truncates artifact, publishes to SSE, persists to Appwrite rounds.

Per-battle validation limits blast radius of the shared key. Routes never appear
in `/docs`.

### 4.4 Judge (host-owned Kimi-K3 default)

- `JUDGE_MODAL_KEY` / `JUDGE_MODAL_SECRET` in `.env` (operator's Modal account) —
  the host default. Sent as `Modal-Key` / `Modal-Secret` headers (existing
  `modal_proxy` auth style).
- Per-battle override: `battles.judge_provider_id` (nullable). If set, judge with
  that user provider instead. Add `judge_provider_id` to `BattleCreate`.
- **Judge role is never a model participant.** Runner filters `judge` out of
  phase participants and always calls `/internal/judge` after real phases
  complete. Seeded phase lists stay as-is; runtime skips the judge role.
- Judge logic ported from user's `judge.py` with review fixes:
  - retry/backoff (3 attempts, exponential).
  - guarded `json.loads` (strip code fences; parse partial output defensively).
  - `model` string from format config (`judge_model`) when present, else host
    default `moonshotai/Kimi-K3`.
  - per-format `judge_rubric` and `scoring_weights` consumed.
  - reasoning redacted before persisting into `scores.justification`.
  - `winner` derived from clamped scores; scores clamped to rubric range (0–100).
  - anti-bias: scores keyed by model_id, never by prompt position.

### 4.5 SSE cross-replica hybrid

- New Appwrite collection `battle_events` — `battle_id`, `event_id` (uuid),
  `payload` (JSON), `created_at` (server timestamp). **No monotonic seq**
  (Appwrite has no atomic counter; multi-writer races are real).
- `event_bus.publish(battle_id, event)` appends locally AND async-writes to
  Appwrite with a fresh uuid (fire-and-forget; on failure, local-only).
- `GET /battles/{id}/stream` merges: Appwrite snapshot + in-process bus.
  Client/SSE merge **sorts by `created_at` then `event_id`**, **dedupes by
  `event_id`**. Reconnect and scale-to-zero safe.
- Heartbeat keep-alive retained.

### 4.6 Sandbox runner framework

`backend/agent_arena/sandbox/`:

- `runner.py` — battle loop (plain Python, transport injected): reads format
  config, maps model_ids → playable roles, iterates phases (skipping judge
  role), calls `/internal/model` per participant, invokes the engine executor,
  streams artifacts via `/internal/round`, calls `/internal/judge` at end.
  Handles `round_visibility` (isolated = opponent artifacts withheld until
  judging; open = streamed live).
- `client.py` — internal API client with `X-Internal-Key`, retry/backoff.
- `executors/__init__.py` — `get_executor(engine) -> Executor`.
- `executors/build_and_break.py`, `same_target_race.py`, `direct_duel.py`,
  `agent_vs_agent.py`, `scripted.py`.

| Engine | Formats | Executor behavior |
|---|---|---|
| build_and_break | 3 (sandbox vs escapee) | Model A emits target code; executor runs it with full sandbox powers (see §4.6.1); model B emits escape attempt; executor detects success/failure via predefined win condition |
| same_target_race | 6 (code review), 7 (debugging) | Both models receive the same target; executor runs fixes/answers against hidden tests; artifact = test results |
| direct_duel | 9 (prompt injection), 10 (jailbreak) | Attacker + defender exchange turns; executor relays sanitized messages; artifact = transcript |
| agent_vs_agent | 12 (two-agent duel) | Models get a thin tool sim (read/write files in sandbox); executor runs turns; artifact = action log |
| scripted | all other 19 | Real model calls via `/internal/model` (user keys or host free), generic phase scaffolding, no bespoke engine logic |

One base image (`debian-slim` + python + httpx + the `agent_arena` package).
Engine behavior selected at runtime by format config `engine` field. Per-format
`timeout_seconds` and `round_visibility` enforced by the runner.

#### 4.6.1 Format 3 exec openness

- Full sandbox powers for inner code: network egress on, real filesystem under a
  battle workdir, subprocess/shell allowed.
- Default inner-exec timeout **180s** (overridable via format config
  `exec_timeout_seconds`).
- Capture stdout/stderr; cwd = battle workdir.
- Escape win condition: predefined (e.g. read a secret file outside workdir, or
  hit a marker HTTP endpoint the executor hosts). Documented in the format's
  `judge_rubric` / executor module.
- Contained by the outer Modal Sandbox resource caps + battle `timeout_seconds`.

### 4.7 Cancel / timeout

- Backend stores `sandbox_id` on the battle doc at spawn.
- `POST /battles/{id}/cancel` → `sandbox.stop()` (immediate) + status=cancelled.
- Runner self-checks battle status each phase (cooperative exit) + in-sandbox
  watchdog thread + backend timeout backstop (marks failed, stops sandbox).

### 4.8 Artifact persistence (Plan 1 override, retained)

Plan 1 changed the original design: rounds persist unconditionally at battle
completion so `/save` works after cold start. Scores persist on completion when
saved (or via idempotent `persist_scores` on later save). Plan 2 keeps this —
do not reintroduce "rounds only if saved".

## 5. Data model changes

- `providers` + `model_name`.
- `battles` + `sandbox_id` (nullable), + `judge_provider_id` (nullable).
- New `battle_events` collection: `battle_id`, `event_id` (uuid), `payload`,
  `created_at`.
- `scores` unchanged structurally; `judge_model` / `justification` now real.

## 6. API changes

- `POST /providers` / `GET /providers` — `model_name` in request/response;
  `GET` also returns the synthetic host free provider.
- `POST /battles` — accepts `judge_provider_id` (optional); validates `model_ids`
  (user providers or `host:openrouter-free`); enforces
  `len(model_ids) == len(playable_roles)`.
- New: `POST /internal/model`, `POST /internal/judge`, `POST /internal/round`
  (all `X-Internal-Key` auth, never exposed via `/docs`).
- `GET /battles/{id}/stream` — merged snapshot+bus delivery; uuid dedupe.
- `POST /battles/{id}/cancel` — force-stops sandbox.

## 7. Error handling & safety

- Provider failures → `/internal/model` returns error → runner marks round
  failed, retries once, then battle failed (spec §8).
- Judge failures → retry 3x, fall back to default Kimi-K3 if override was set,
  else fail battle.
- Artifact redaction (existing `redact.py`) applied in `/internal/round` before
  SSE + persist (redact-then-truncate, per Plan 1 fix).
- No secrets in sandboxes; keys only decrypted in backend.
- Concurrency cap (5 active/user) unchanged.
- `INTERNAL_API_KEY` / `HOST_OPENROUTER_KEY` / judge secrets never exposed via
  `/docs`; internal routes require the header.

## 8. Testing

- **Fast hermetic suite** (`pytest tests/ --ignore=tests/evals`, default):
  - provider linkage validation (battle rejects foreign/unknown model_ids;
    accepts `host:openrouter-free`).
  - provider layer `get_model_call_spec` round-trip (encrypt/decrypt/mask) +
    host free resolution.
  - role mapping: order-preserving, judge role skipped, length mismatch → 400.
  - judge module: guarded JSON parse, redaction of reasoning, retry/backoff,
    clamped scores, per-format rubric/weights.
  - SSE merge: Appwrite snapshot + bus dedupe by `event_id`, sort by
    `created_at` then `event_id`.
  - runner logic with injected fake transport + fake backend (no Modal).
  - cancel force-stop path with a fake sandbox handle.
  - format-3 executor unit tests with a local subprocess (no Modal).
- **Modal-gated suite** (`pytest -m modal` only; **skipped by default**):
  ONE real sandbox battle — format 9 (prompt injection vs hygiene) — verifying
  spawn → `/internal/model` → executor → `/internal/judge` → `/internal/round`
  → SSE → persistence.

## 9. Deployment

- `.env.example` += `INTERNAL_API_KEY`, `JUDGE_MODAL_KEY`, `JUDGE_MODAL_SECRET`,
  `HOST_OPENROUTER_KEY`.
- `modal_entry.py`: sandbox spawn uses the base image with `INTERNAL_API_KEY`
  as env secret; backend env also has judge + OpenRouter keys.
- Seed `battle_events` collection on deploy (schema).
- **Never commit real keys.** Rotate any key that appeared in chat.

## 10. Out of scope (deferred)

- Remaining 19 formats' bespoke engine logic (scripted fallback only).
- Frontend (Plan 3).
- High-complexity / arms-race formats' real executors.
