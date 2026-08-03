# Agent Arena — Plan 3: Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Next.js web app in `modal/frontend/` with Appwrite auth and full 6-page UI against the live Modal backend.

**Architecture:** Browser talks to Appwrite for auth (JWT) and to Modal FastAPI for all data. No Next.js BFF. Dark shadcn UI.

**Tech Stack:** Next.js 15 App Router, TypeScript, Tailwind 4/3, shadcn/ui, appwrite SDK, Vercel-ready.

## Global Constraints

- Frontend root: `modal/frontend/`
- Modal URL default: `https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run`
- Auth: Appwrite email/password → JWT → `Authorization: Bearer`
- Host free model id: `host:openrouter-free`
- Never commit secrets; only `NEXT_PUBLIC_*` in frontend env

---

### Task 1: Scaffold Next.js app

**Files:**
- Create: `modal/frontend/**` via create-next-app

- [x] **Step 1: Scaffold**

```bash
cd /Users/villain/modal
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --turbopack=false
```

- [x] **Step 2: Install deps**

```bash
cd frontend && npm i appwrite && npx shadcn@latest init -y -d
npx shadcn@latest add button card input label select badge tabs toast textarea separator dropdown-menu
```

- [x] **Step 3: Env example**

Create `frontend/.env.example` and `frontend/.env.local` with Appwrite + Modal URLs.

- [x] **Step 4: Commit**

```bash
git add modal/frontend && git commit -m "feat(frontend): scaffold Next.js + tailwind + shadcn"
```

### Task 2: Appwrite auth + API client

**Files:**
- Create: `frontend/src/lib/appwrite.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth-context.tsx`

- [x] **Step 1: appwrite.ts** — client, account helpers (signup, login, logout, jwt)
- [x] **Step 2: api.ts** — `apiGet/Post` with Bearer JWT; streamBattle SSE parser
- [x] **Step 3: AuthProvider** — session restore, jwt refresh, useAuth hook
- [x] **Step 4: Commit**

### Task 3: Shell layout + auth pages

**Files:**
- Create: `frontend/src/components/site-header.tsx`
- Create: `frontend/src/app/layout.tsx` (dark theme)
- Create: `frontend/src/app/login/page.tsx`, `signup/page.tsx`

- [x] **Step 1: Dark layout + nav**
- [x] **Step 2: Login/signup forms**
- [x] **Step 3: Commit**

### Task 4: Home + formats grid

**Files:**
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/format-card.tsx`

- [x] **Step 1: Fetch GET /formats (with optional auth)**
- [x] **Step 2: Filter by engine**
- [x] **Step 3: Commit**

### Task 5: Providers page

**Files:**
- Create: `frontend/src/app/providers/page.tsx`

- [x] **Step 1: List providers (host free first)**
- [x] **Step 2: Add form with model_name**
- [x] **Step 3: Commit**

### Task 6: Create battle page

**Files:**
- Create: `frontend/src/app/battles/new/page.tsx`

- [x] **Step 1: Format select, model multi-select (len = playable roles), options**
- [x] **Step 2: POST /battles → redirect /battles/[id]**
- [x] **Step 3: Commit**

### Task 7: Live battle page (SSE)

**Files:**
- Create: `frontend/src/app/battles/[id]/page.tsx`
- Create: `frontend/src/components/battle-stream.tsx`

- [x] **Step 1: SSE consumer + event log UI**
- [x] **Step 2: Stop + Save buttons**
- [x] **Step 3: Commit**

### Task 8: Leaderboard + History

**Files:**
- Create: `frontend/src/app/leaderboard/page.tsx`
- Create: `frontend/src/app/history/page.tsx`
- Modify backend if needed: `GET /battles`

- [x] **Step 1: Leaderboard scopes**
- [x] **Step 2: History via GET /battles?saved=true (add endpoint if missing)**
- [x] **Step 3: Commit**

### Task 9: Polish + README + verify

**Files:**
- Create: `frontend/README.md`
- Vercel-ready `frontend/vercel.json` if needed

- [x] **Step 1: Loading/error states, toasts**
- [x] **Step 2: Document env + Appwrite platform setup**
- [x] **Step 3: `npm run build` must pass**
- [x] **Step 4: Commit**

---

**Execution:** Prefer inline in this session (user asked to continue building).
