# Architecture Map — Agent Arena

## Layers

```
Frontend (Vite React)
  lib/api.ts (BASE = VITE_MODAL_URL fallback prod)
  lib/auth.ts (Zustand, safeGet/Set, JWT 10min refresh)
  lib/appwrite.ts (Appwrite client singleton)
  pages: Home (formats), NewBattle (role mapping), LiveBattle (SSE), Leaderboard, History, Providers, Design*

Backend (FastAPI on Modal)
  main.py (CORS, routers)
  config.py (settings APPWRITE_*, etc)
  auth.py (get_current_user JWT verify)
  db.py (get_databases Appwrite Databases client)
  battles.py (create, list, get, stream via event_bus, cancel, save)
  formats.py (list)
  providers.py (CRUD, is_host_model, host: prefix)
  leaderboard_router.py (elo)
  internal_router.py (internal token)
  event_bus.py (publish, subscribe, load_durable with created_at+event_id ordering, seen_ids dedup)
  judge.py (host judge Kimi-K3, retry x3, clamp)
  sandbox_launcher.py (Modal sandbox spawn/stop)
  sandbox/entrypoint.py (sets ARENA_IN_SANDBOX=1)
  sandbox/client.py (InternalClient: round + judge + sanitize_artifact)
  sandbox/runner.py (generic runner)
  sandbox/executors/base.py (Executor.run_battle phase loop, halted, finish judge, guard, emit_result)
  sandbox/executors/formats/* (9 bespoke: rev_shell, payload, polymorph, cred_reuse, arms_race, exploit_patch, time_siege, digital_twin, same_defense_adaptive)
  seed_formats.py (slugify truncation 36, name+slug registry)
  crypto.py (Fernet encrypt)
  redact.py (sanitize_artifact)
  elo.py, leaderboard.py

Infra
  Modal: modal_entry.py FastAPI app, sandbox image
  Vercel: frontend/vercel.json rewrite /* -> /index.html SPA
  Appwrite: collections battles, providers, formats, rounds, leaderboard
```

## Data Flows

1. **New Battle:** User picks format → playableRoleCount (filter judge) → model_ids length must match → _validate_model_ids ownership → create_document battles queued → Background task sandbox_launcher.start_battle → sandbox entrypoint sets env → runner loads format config phases → for phase in phases: run_phase → client.round with artifact events → event_bus.publish → judge → scores event → battle completed → persist_scores if saved.

2. **Live Stream:** GET /battles/{id}/stream (auth + _get_owned) → load_durable snapshot dedup seen_ids → loop subscribe sorted by created_at+event_id → yield heartbeat + battle_status → completion → done event. Frontend streamBattle() reads SSE, parses event: + data: lines, accumulates arts[200].

3. **Formats:** GET /formats public? api.formats(null) no token but formats.py router maybe auth? Frontend public load immediately; backend may allow null? Need check auth dep optional.

4. **Providers BYOK:** User creates provider with base_url, api_key, auth_style, model_name → crypto encrypt → stored encrypted_key → masked_key returned (last 4). Host providers id starts with host: allowed even if not owned.

## Trust Boundaries

- BYOK keys: user -> frontend (input) -> backend encrypt -> Appwrite encrypted_key. Never log, never return full. Frontend only sees masked.
- Sandbox: untrusted agent code must stay under arena-tools root, .. rejection, timeout kill, output cap, gate, redact.
- Battle access: user_id ownership via _get_owned.
- Host free default: nemotron-3-ultra:free etc, no key needed, backend proxies.

## Current Gaps Noted

- Home formats.length || 25 fallback hides bug where backend returns [] due to CORs or env missing.
- Auth interval leak in useAuth.init() called every SiteHeader mount but setInterval not cleared.
- Executor registry: 9 executors but seed may have 25 claimed -> need 25 bespoke check.
- SSE polling time.sleep blocking vs async.
