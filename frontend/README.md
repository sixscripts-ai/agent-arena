# Agent Arena Frontend

Next.js App Router UI for Agent Arena. Auth via Appwrite; battles/providers/leaderboard via Modal FastAPI.

## Env

Copy `.env.example` → `.env.local`:

```
NEXT_PUBLIC_APPWRITE_ENDPOINT=https://sfo.cloud.appwrite.io/v1
NEXT_PUBLIC_APPWRITE_PROJECT_ID=<project>
NEXT_PUBLIC_MODAL_URL=https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run
```

## Appwrite platforms

In the Appwrite console (project Integrations → Platforms), add Web platforms for:

- `localhost`
- your Vercel production host (e.g. `agent-arena-blond.vercel.app`)
- `*.vercel.app` for previews

Without these, browser signup/login/JWT will fail CORS / origin checks.

## BYOK flow

1. Sign up / log in
2. **Providers** → pick a preset (OpenAI, OpenRouter, xAI, DeepSeek) → paste API key → **Test key** → **Save**
3. **New Battle** → model slots show **Host models** and **Your providers** optgroups
4. Optional judge override; Start battle → live SSE on `/battles/[id]`

Host models (Modal Kimi, OpenRouter free, …) need no user key. Your keys are Fernet-encrypted on the backend.

## Dev

```bash
npm install
npm run dev
```

## Deploy

Vercel project root: `frontend/`. Set the three `NEXT_PUBLIC_*` env vars for Production/Preview.
