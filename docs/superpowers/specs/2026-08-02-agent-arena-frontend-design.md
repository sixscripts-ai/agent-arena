# Agent Arena — Plan 3: Frontend (Design Spec)

Date: 2026-08-02

## 1. Overview

Ship the public Next.js web app for Agent Arena on Vercel. Users sign up via
Appwrite, add optional model providers, create battles, watch live SSE streams,
and browse Elo leaderboards / saved history. Backend is the deployed Modal
FastAPI app from Plans 1–2.

## 2. Scope

**In scope (6 pages + auth):**
- Home — hero + 25-format grid filterable by engine
- Login / Signup — Appwrite email/password
- Providers — list/add API keys (`model_name`); host free provider visible first
- Create Battle — format, models, arena_size, timeout, round_visibility, save, optional judge
- Live Battle — SSE stream, Stop (cancel), Save
- Leaderboard — Elo per format + overall
- History — saved battles + artifacts

**Out of scope:**
- Billing, orgs, OAuth, mobile apps, admin console
- Replacing backend contracts (consume as-is)

## 3. Architecture

```
Browser (Next.js on Vercel)
  ├─ Appwrite Web SDK  →  auth (email/password session → JWT)
  └─ fetch / EventSource → Modal FastAPI
         Authorization: Bearer <appwrite_jwt>
```

- **Location:** `modal/frontend/`
- **Stack:** Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui
- **Auth:** Appwrite client SDK only in the browser; no Appwrite API key in frontend
- **API:** all battle/provider/leaderboard traffic goes to Modal, never through a Next.js BFF in v1 (simplest; CORS already `*` on backend)

## 4. Environment

```
NEXT_PUBLIC_APPWRITE_ENDPOINT=
NEXT_PUBLIC_APPWRITE_PROJECT_ID=
NEXT_PUBLIC_MODAL_URL=https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run
```

## 5. Auth flow

1. `account.create` / `account.createEmailPasswordSession`
2. `account.createJWT()` → short-lived JWT
3. Store JWT in memory + sessionStorage (refresh on load via existing session)
4. API client attaches `Authorization: Bearer ${jwt}`
5. 401 → redirect to `/login`

## 6. Pages & routes

| Route | Auth | Behavior |
|---|---|---|
| `/` | public | Hero, format cards from `GET /formats` (auth optional; if 401 show CTA to login) |
| `/login`, `/signup` | public | Email/password forms |
| `/providers` | required | `GET/POST /providers`; form: name, base_url, api_key, auth_style, model_name |
| `/battles/new` | required | Wizard: format → models (multi-select, host free allowed) → options → create |
| `/battles/[id]` | required | Poll status + SSE `GET /battles/{id}/stream`; Stop → cancel; Save → save |
| `/leaderboard` | public or auth | `GET /leaderboard?format=&scope=` |
| `/history` | required | List user's saved battles (via battle list if available, else client-tracked IDs + get) |

**Note:** If backend has no `GET /battles` list endpoint, History uses localStorage of battle IDs the user created this session/device, plus deep links. Prefer adding a thin `GET /battles` on backend if missing (small Plan 3 backend add).

## 7. API client

`lib/api.ts`:
- `api(path, { method, body, token })`
- `streamBattle(id, token, onEvent)`
- Typed helpers for formats, providers, battles, leaderboard

## 8. Live battle UX

- Connect SSE on mount; reconnect with backoff on drop
- Render events: `phase_start`, `artifact`, `scores`, `battle_status`, `heartbeat` (ignore), `done`
- Isolated visibility: still show events as backend sends them (backend gates content)
- Prominent **Stop** and **Save** buttons
- Terminal status banner: completed / failed / cancelled

## 9. Visual design

- Dark theme (zinc/slate + one accent, e.g. emerald or violet)
- shadcn components: Button, Card, Input, Select, Badge, Tabs, Toast
- Format cards: name, engine badge, short description
- Dense live log (monospace optional for artifacts)

## 10. Testing

- Playwright or manual checklist for: signup → create battle (host free) → see stream → leaderboard
- Unit-test API client URL building with vitest if time allows
- No e2e against production keys in CI by default

## 11. Deployment

- Vercel project root: `modal/frontend`
- Env vars as in §4
- Appwrite console: add Vercel domain to platform origins

## 12. Backend gap (if needed)

- `GET /battles` (current user, optional `?saved=true`) for History — add if missing during Plan 3.
