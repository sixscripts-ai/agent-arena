# Agent Arena — Technical Architecture Document (Greenfield Frontend)

## 1. Architecture Design
```mermaid
graph TD
  subgraph Frontend [Frontend - Vite + React + Tailwind - Vercel]
    A[React Router] --> B[Pages: Home, Auth, Providers, NewBattle, LiveBattle, Leaderboard, History]
    B --> C[Lib: api.ts (fetch + SSE), appwrite.ts (auth), auth-context.tsx (JWT refresh 10min)]
    C --> D[Components: CodePane (dual streaming), PhaseStepper, JudgeStrip, FormatCard (brutalist)]
  end

  subgraph Backend [Backend - Modal FastAPI - Existing]
    E[FastAPI app /health public, /formats public, /leaderboard public, /battles auth, /providers auth, /internal X-Internal-Key]
    F[Appwrite SDK - providers, battles, rounds, battle_events, formats, leaderboard, scores]
    G[Providers: HOST_PROVIDERS list - OpenRouter, DeepSeek, Groq, etc - env HOST_*_KEY]
    H[Sandbox Runner: runner.py phase loop, executors/build_and_break 180s, same_target_race, direct_duel, agent_vs_agent, scripted]
    I[Judge: Kimi-K3 host via Modal proxy Modal-Key/Secret, retry x3, redacted justification]
  end

  Frontend -- "Bearer <Appwrite JWT>" --> E
  Frontend -- "EventSource GET /battles/{id}/stream" --> E
  E -- "decrypt Fernet" --> F
  E -- "spawn" --> H
  H -- "HTTP X-Internal-Key /internal/model|judge|round" --> E
```

## 2. Technology Description
- Frontend: React@18 + TypeScript@5 + Vite@5 + TailwindCSS@3.4.1 + react-router-dom@6 + Zustand@4 (auth/battle state) + Appwrite SDK@15 (auth only)
- Initialization Tool: vite-init template react-ts (pnpm create vite-init)
- Backend: Existing Modal FastAPI (Python 3.11, Appwrite, Modal Sandboxes) — no change except P0 fixes already deployed: public formats/leaderboard, CORS locked to vercel.app, redact expanded, compare_digest
- Database: Appwrite Cloud (project 6a6f9133001ed182210d, database 6a6f9342000fc7aebdcd) — collections: providers, battles, rounds, battle_events, formats (25 seeded), leaderboard, scores
- External Services: OpenRouter free (Nemotron), DeepSeek (HOST_DEEPSEEK_KEY), Groq, Modal Kimi-K3 judge proxy

## 3. Route Definitions
| Route | Purpose |
|-------|---------|
| / | Home — public formats grid (GET /formats public), stats, hero with live count |
| /login | Login — email/password, redirect ?next=, error states |
| /signup | Signup — name, email, password>=8, auto login + JWT |
| /providers | Keys — list host (read-only, blue border) vs your providers, add/edit form with 15 presets, test key via POST /providers/health |
| /battles/new | New Battle Wizard — format picker, model slots (order=role mapping), judge optional, timeout/visibility, POST /battles |
| /battles/:id | Live Battle — dual code panes streaming real artifacts via SSE, phase stepper, Stop (cancel) + Save, judge strip |
| /leaderboard | Leaderboard — public, Elo per overall or per format (GET /leaderboard?format=overall) |
| /history | History — saved battles GET /battles?saved=true + localStorage arena_battle_ids fallback, logbook style |
| /preview | Preview — internal design showcase (existing from Step 0, will be removed after redesign) |

## 4. API Definitions
```typescript
// api.ts
type FormatOut = { id: string; name: string; engine: string; description?: string; slug?: string; roles?: string[]; config?: any }
type ProviderOut = { id: string; name: string; base_url: string; masked_key: string; auth_style: string; model_name: string }
type ProviderCreate = { name: string; base_url: string; api_key: string; auth_style: string; model_name: string }
type BattleCreate = { format_id: string; model_ids: string[]; arena_size: number; timeout_seconds: number; round_visibility: "isolated"|"open"; save: boolean; judge_provider_id?: string|null }
type BattleOut = { id: string; user_id: string; format_id: string; model_ids: string[]; arena_size: number; status: string; timeout_seconds: number; round_visibility: string; saved: boolean; sandbox_id?: string }
type ArtifactOut = { phase: string; model_id: string; artifact: string }
type LeaderboardRow = { model_id: string; format_id?: string; elo: number; games_played: number; rank?: number }
type StreamEvent = { event: string; data: any }

// Appwrite auth
// POST /account (create), POST /account/sessions/email (login), GET /account (session user), POST /account/jwts (createJwt) -> JWT 15min expiry, refresh every 10min
// Modal API
// GET /formats (public after P0), GET /leaderboard?format=overall (public)
// GET /providers, POST /providers, POST /providers/health (auth)
// POST /battles, GET /battles/:id, GET /battles?saved=true, POST /battles/:id/cancel, POST /battles/:id/save (auth)
// GET /battles/:id/stream SSE (auth) -> events: phase_start, artifact, scores, battle_status, done, heartbeat
```

## 5. Server Architecture Diagram
Existing backend (no new server, frontend pure SPA):
```
Controller (FastAPI Router)
  -> Service (battles.py: create_battle validates len(model_ids)==playable_roles, arena_size==len, is_host_model allows any host:)
  -> Repository (db.py: get_databases, TablesDB list_rows/create_row with Query)
  -> Database (Appwrite)
  -> Sandbox (sandbox_launcher.py: start_battle -> try_spawn_modal_sandbox with BATTLE_BOOTSTRAP_JSON or in-process direct runner)
```

## 6. Data Model
### 6.1 Data Model Definition
```mermaid
erDiagram
  PROVIDERS {
    string id PK
    string user_id FK
    string name
    string base_url
    string encrypted_key
    string masked_key
    string auth_style
    string model_name
  }
  FORMATS {
    string id PK
    string name
    string engine
    string config JSON
  }
  BATTLES {
    string id PK
    string user_id FK
    string format_id FK
    string[] model_ids
    int arena_size
    string status
    int timeout_seconds
    string round_visibility
    boolean saved
    string sandbox_id optional
    string judge_provider_id optional
  }
  ROUNDS {
    string id PK
    string battle_id FK
    string phase
    string model_id
    string artifact (100kb cap, redacted)
  }
  BATTLE_EVENTS {
    string id PK
    string battle_id FK
    string event_id uuid
    string payload JSON
    float created_at
  }
  SCORES {
    string id PK
    string battle_id FK
    string model_id
    float score
    string judge_model
    string justification redacted
  }
  LEADERBOARD {
    string id PK
    string model_id
    string format_id
    float elo
    int games_played
  }
```

### 6.2 Data Definition Language
Appwrite collections already exist. Required P0 fix: ensure indexes (battles.user_id, user_id+status, user_id+saved, providers.user_id+name, rounds.battle_id, scores.battle_id, battle_events.battle_id+created_at) — note attribute length 262144 blocks index creation, need to recreate with length 36-128 for indexed fields (future migration). Frontend uses localStorage arena_battle_ids as fallback for history when GET /battles not available.
