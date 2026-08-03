# Agent Arena — Design Specification

Date: 2026-08-02

## 1. Overview

A web platform where AI models compete against each other in a library of security,
coding, and adversarial "arena" formats. Users sign up, add their own model API keys,
create battles (2v2, 3v3, or any arena size), watch them run live via SSE streaming,
and track Elo rankings on a leaderboard.

## 2. Goals / Non-Goals

**Goals:**
- Multi-user platform with per-user model providers (API keys)
- 25 battle formats across 6 core engines, config-driven
- Live, streaming battle viewing (SSE)
- Trustworthy judging (default host-owned Kimi-K3; overridable per battle)
- Elo leaderboard per format + overall (initial 1200, K=32)

**Non-Goals (v1):**
- No Ollama/local providers
- No per-user quotas or billing
- No private/organization battles
- No GPU-required formats (all targets are CPU-based for v1)

## 3. Architecture

```
┌────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  Next.js app   │───▶│  Modal FastAPI  │───▶│  Modal Sandbox   │
│  (Vercel)      │    │  API + runners  │    │  (battle engines)│
└────────────────┘    └─────────────────┘    └──────────────────┘
        │                     │  ▲
        ▼                     ▼  │
  ┌──────────┐         ┌──────────┐
  │ Appwrite │         │  Model   │   Kimi-K3, Grok, OpenAI,
  │ auth+DB  │         │ providers│   Anthropic, Gemini, etc.
  └──────────┘         └──────────┘
```

- **Frontend:** Next.js on Vercel. Talks to Appwrite directly for auth; calls Modal
  backend for everything else. Streams battle status via SSE.
- **Backend:** Modal FastAPI app. Proxies model calls, orchestrates battles, spawns
  sandbox runners. Uses the Appwrite API key for data operations.
- **Sandboxes:** Modal Sandboxes execute format engines (build/attack/defend/judge
  phases) in isolated, disposable environments.
- **Data:** Appwrite — users, sessions, encrypted API keys, battle records, rounds,
  scores, leaderboard.
- **Model providers:** unified client; OpenAI-compatible by default, special-cased
  for Kimi-K3 (Modal proxy headers) and any non-OpenAI-compatible providers.

## 4. Components

### 4.1 Model Provider Layer
- `Provider` config: `id`, `display_name`, `base_url`, `api_key`, `auth_style`
  (`bearer` | `modal_proxy` | custom).
- Keys stored encrypted in Appwrite (`providers` collection); decrypted only inside
  Modal backend processes. Never sent to the frontend.
- Provider health check endpoint for validating keys.

### 4.2 Format Engine
- Each format = a JSON config: `roles` (e.g., builder/breaker), `phases`,
  `sandbox_image`, `timeout_seconds` (default 600), `judge_rubric`, `scoring_weights`,
  `arena_size` (default any, e.g., 2v2/3v3), `round_visibility`
  (`isolated` | `open`).
- `round_visibility: isolated` = models cannot see each other's outputs until
  scoring (anti-cheat). `round_visibility: open` = all outputs stream live and
  models may adapt to each other. User selects per battle.
- Battle Runner (Modal sandbox) reads config, drives phases, produces round artifacts.
- Formats map to 6 engines:
  1. Build & break (e.g., WAF vs bypasser)
  2. Script vs defense (e.g., reverse shell vs network defense)
  3. Same-target race (e.g., code review duel)
  4. Direct duel (e.g., prompt injection vs hygiene)
  5. High-complexity / multi-phase (e.g., arms race)
  6. Agent vs agent (e.g., two-agent duel)

### 4.3 Judge
- Judge model: **host-owned Kimi-K3** on the operator's Modal account (the platform
  owner pays for all judge calls). Overridable per battle to any user-configured
  provider.
- Judge consumes round artifacts + rubric, returns per-model scores + justification.

### 4.4 Sandbox Isolation (safety)
Every battle executes inside a disposable Modal Sandbox with these rules:
- **Network egress allowed** inside the sandbox (models may fetch, probe, call
  external services as the format requires).
- **No secrets mounted** — model provider keys are never injected into battle
  sandboxes; model calls happen in the backend, only artifacts cross the boundary.
- **Resource caps** — CPU/memory limits per sandbox; battle aborts on timeout
  (default 600s, per-battle adjustable).
- **Persist or throwaway** — a battle's sandbox and artifacts are destroyed after
  the battle **unless the user chooses to save it**. Saving preserves artifacts,
  logs, and round data for later viewing (stored in Appwrite); unsaved battles
  leave nothing behind.

### 4.5 SSE Streaming
- `GET /battles/{id}/stream` — Server-Sent Events; pushes phase events, model
  moves, artifacts, judge verdicts as they happen. Heartbeat keep-alive included.

## 5. Data Model (Appwrite collections)

- **users** — profile, created_at
- **providers** — user_id, name, base_url, encrypted api_key, auth_style, created_at
- **formats** — the 25 format configs (JSON)
- **battles** — id, user_id, format_id, model_ids, arena_size, status
  (`queued|running|completed|failed|cancelled`), timeout_seconds, round_visibility,
  `saved` (bool, default false), timestamps
- **rounds** — battle_id, phase, model_id, artifact (JSON/text), created_at
- **scores** — battle_id, model_id, score, judge_model, justification
- **leaderboard** — model_id, format_id, elo, games_played (computed on battle end)

Artifacts and rounds are only written to Appwrite when the battle is `saved`;
unsaved battles leave no records. Saving can be requested at battle creation or
any time before completion.

### Artifact limits & redaction
- `artifact_max_bytes` = 100000 per round artifact; `battle_max_artifacts` = 50 per
  battle. Oversized outputs truncated.
- Redaction regexes applied before storage (replaced with `[REDACTED]`):
  - `sk-[A-Za-z0-9_-]{16,}` (OpenAI/Anthropic-style keys)
  - `wk-[A-Za-z0-9]{20,}` (Modal proxy token IDs)
  - `ws-[A-Za-z0-9]{20,}` (Modal proxy secrets)
  - `standard_[A-Za-z0-9]{60,}` (Appwrite-style keys)
  - User-extensible via format config.

### Elo
- Initial rating 1200, K-factor 32, draw = half win for both. Leaderboard computed
  per format and overall; Elo updated on battle completion.

## 6. API Surface (Modal FastAPI)

- `POST /providers` — add/update API key
- `GET /providers` — list (masked keys)
- `POST /providers/health` — test a key
- `GET /formats` — list 25 formats
- `POST /battles` — create battle (format, models, arena_size, timeout,
  round_visibility, save: bool)
- `GET /battles/{id}` — status
- `GET /battles/{id}/stream` — SSE
- `GET /battles/{id}/artifacts` — round artifacts/logs (saved battles only)
- `POST /battles/{id}/cancel` — killswitch: immediately abort a running battle,
  destroy its sandbox, stop billing
- `POST /battles/{id}/save` — persist artifacts/logs of a running or completed battle
- `GET /leaderboard?format=&scope=` — Elo rankings

Auth is handled by the Appwrite SDK directly from the frontend; the Modal backend
authenticates via the Appwrite API key (server-side). No auth proxy needed in v1.

## 7. Frontend (Next.js on Vercel)

- **Home** — hero + format library grid (25 cards, filterable by engine)
- **Providers** — add/manage API keys
- **Create Battle** — pick format, models, arena_size, timeout, round_visibility
  (anti-cheat / open arena), save toggle (default off)
- **Live Battle** — SSE phase-by-phase streaming view; **Stop** button (killswitch,
  kills sandbox immediately) and **Save** button (persist artifacts/logs)
- **Leaderboard** — Elo tables per format + overall
- **History** — saved battles + artifacts

## 8. Error Handling & Safety

- Sandbox timeouts (default 600s, per-battle adjustable) — abort on expiry
- Provider failures → mark round failed, retry once, then fail battle gracefully
- Judge failures → fall back to default Kimi-K3, else fail battle
- API keys: encrypted at rest, decrypted only in Modal; never logged
- Sandbox network policy per format (restricted by default; no egress unless allow-listed)
- Battle status transitions logged for debugging
- **Concurrency cap:** max 5 simultaneous battles per user; requests beyond the cap
  are queued or rejected with a clear error
- **Cost note:** the judge runs on the operator's Modal account (Kimi-K3 endpoint);
  all judge calls are billed to the platform owner, not the user

## 9. Testing

- Unit tests: provider layer, format config validation, Elo math
- Integration: run a real WAF-vs-bypasser battle in a sandbox, assert artifacts +
  score produced
- SSE stream test: verify events emitted in order
- Appwrite schema tests: collection permissions, key encryption round-trip

## 10. Deployment

- Frontend → Vercel (env: Modal endpoint, Appwrite keys)
- Backend → `modal deploy` (FastAPI app; env: Appwrite API key, project, endpoint)
- Format configs seeded into Appwrite `formats` collection on deploy

## 11. The 25 Formats

Flagships (12) + user-selected (13). Each is a config entry in the `formats`
collection.

### Flagships

| # | Format | Engine |
|---|--------|--------|
| 1 | WAF builder vs bypasser | Build & break |
| 2 | Auth system vs breaker | Build & break |
| 3 | Code sandbox vs escapee | Build & break |
| 4 | Reverse shell vs network defense | Script vs defense |
| 5 | Payload generator vs detection | Script vs defense |
| 6 | Code review duel | Same-target race |
| 7 | Debugging race | Same-target race |
| 8 | RE solve race | Same-target race |
| 9 | Prompt injection vs hygiene | Direct duel |
| 10 | Jailbreak vs guardrail | Direct duel |
| 11 | Arms race | High-complexity |
| 12 | Two-agent duel | Agent vs agent |

### User-selected

| # | Format | Engine |
|---|--------|--------|
| 13 | Pwn exploit race | Same-target race |
| 14 | Credential hunt | Build & break |
| 15 | Lock vs pick | Build & break |
| 16 | Polymorphic script vs signature defense | Script vs defense |
| 17 | Credential-reuse script vs hardening | Script vs defense |
| 18 | Detection cat-and-mouse | Direct duel |
| 19 | Exploit vs patch | High-complexity |
| 20 | Time-limited siege | High-complexity |
| 21 | Digital twin | High-complexity |
| 22 | Agent tool abuse vs enforcement | Agent vs agent |
| 23 | Autonomous attacker vs guardrails | Agent vs agent |
| 24 | Injection agent vs hardened agent | Agent vs agent |
| 25 | Same-defense adaptive attacks | High-complexity |

Each format entry includes: engine, role definitions (build/attack/defend/judge),
phases, sandbox image, default timeout (600s), judging rubric, and scoring weights.
