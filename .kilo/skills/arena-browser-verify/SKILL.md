---
name: arena-browser-verify
description: Browser verification and E2E smoke for Agent Arena webapp. Automates Playwright + local dev server startup, navigates https://agent-arena-blond.vercel.app and localhost:3010, checks rendering, console errors, network health, SSE streaming, battle flow from signup to live battle. Use after any UI or API change, before deploy, or when user asks verify in browser, smoke test, check live site. Triggers: verify browser, smoke test, check rendering, console errors, network health, E2E verification.
---

# Arena Browser Verify

Specialized verifier that spins up dev servers and checks Agent Arena like a user would.

## When to Use

- After changing frontend/src or backend routes
- Before Vercel deploy
- Live site https://agent-arena-blond.vercel.app shows "Format library 0" or broken streaming
- User says "verify in browser", "check rendering", "smoke test"

## Environment Assumptions

- Local frontends:
  - arena-work/frontend runs on http://localhost:3010 (vite dev)
  - agent-arena-builder has no frontend — but can proxy arena-work
- Backend:
  - Modal prod: https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run (or VITE_MODAL_URL env)
  - Mock judge mode: ARENA_USE_MOCK=1 / localhost:8001 legacy
- Playwright MCP available (if not, fall back to puppeteer / browser_use)

## Workflow

### Step 1 - Preflight Checks

Run `scripts/preflight.py`:

- Check `frontend/.env` or env.local: VITE_MODAL_URL, VITE_APPWRITE_ENDPOINT, PROJECT_ID
- Check backend health: curl /health → {status ok}
- Check prod health: curl https://agent-arena-blond.vercel.app (follow redirect) + backend health URL
- Verify pnpm / node available

Outputs `reports/preflight.json`

### Step 2 - Start Dev Server (if verifying locally)

Use background_process tool or bash:

```
cd /Users/villain/Projects/arena-work/frontend
pnpm run dev -- --port 3010 --host
```

Wait ready pattern: `Local:` or `ready` or port 3010 ready (use ready.port:3010)

Store process id for later stop.

### Step 3 - Browser Automation

Via playwright_browser_* tools or puppeteer, execute checklist:

**Home / Arena**

1. Navigate to / or live URL
2. Snapshot accessibility tree, ensure:
   - Hero "Models fight." present
   - LIVE • 8 battles badge present
   - Start battle button navigates to /signup or /battles/new conditional on auth
   - Format library count ≠ 0 after load — wait for network idle, check if formats >0 else report bug
   - Console messages level error =0 (except known font warnings)
   - Network requests: /formats 200, status? Check response

**Auth Flows**

- /login renders inputs, Log in button
- /signup renders name/email/pass
- Check error boundary: invalid login shows message not crash

**NewBattle (requires auth)**

- Without login: shows "Login required"
- With mocked JWT (if possible) or manual login via UI:
  - Formats select populated
  - Slots count matches playable roles (roles from format)
  - Host free vs Your optgroups present
  - Start battle disabled when busy, err display

**LiveBattle**

- Mock battle via localStorage ids (arena_battle_ids) or via API createBattle if JWT present
- Check dual CodePane rendering, line numbers, status pill, heartbeat
- Check SSE: open /battles/:id/stream request succeeds (if auth)
- Event stream auto-scroll

**Leaderboard / History**

- Leaderboard table renders, select Overall vs per-format
- History: if no saved, CTA Create battle

**Resp / A11y / Visual**

- Resize to 375x800 (mobile) and 1360x800 (desktop) — header nav collapses to ☰
- Check focus-visible outline present
- Dark mode: toggle via useTheme, check code-bg stays #0A0A0A intentional
- Lighthouse quick: no console errors, no failed fetch

### Step 4 - Console & Network Health

Collect via tools:

- `playwright_browser_console_messages` level error, all=true → report
- `playwright_browser_network_requests` filter `/api|/formats|/battles|/leaderboard` → check 4xx/5xx
- Verify vercel.json rewrite: direct /battles/new → index.html serves correct (not 404)

### Step 5 - Generate Report

Run `scripts/gen_verification_report.py` → `reports/browser-verify.html`

Sections:
- Screenshots (home desktop + mobile, live battle, leaderboard)
- Console errors list (pass/fail)
- Network failed requests
- User flow pass/fail (checklist)
- Recommendations (e.g., "formats endpoint 500 due to CORS or missing env")

Include curl checks for prod:

```
curl -s https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run/health
curl -s https://agent-arena-blond.vercel.app | grep "Format library"
```

### Step 6 - Teardown

- Stop dev server background process
- Cleanup env

## Scripts & References

- `scripts/preflight.py` — env + health checks
- `scripts/smoke_playwright.py` — headless Playwright script alternative to MCP (navigates localhost:3010 and prod)
- `references/checklist.md` — step-by-step manual checklist for arena-specific routes
- `references/common-failures.md` — known issues: formats 0 (VITE_MODAL_URL missing), engines 0, 404 due to vercel rewrites, JWT expiry, SSE 403
- `assets/test-creds.json.template` — local test creds shape (never commit real)

## Success Criteria

- Home renders, formats >0 or error UI explains why (not just "Loading…")
- No console errors (except allowed warnings: font loading)
- No network 4xx/5xx for /formats, /health
- NewBattle shows correct slot count (2 for builder/breaker, N for multi-role)
- LiveBattle shows dual panes, streaming indicator, SSE connected
- Mobile header hamburger works, nav links valid

## Troubleshooting

- If formats 0: check `api.ts` BASE fallback, VITE_MODAL_URL env in vercel dashboard, backend CORS regex, backend formats collection empty
- If SSE fails: check JWT expiry (10min refresh), _get_owned ownership, event_bus durable empty
- If dev server fails: pnpm install, port 3010 busy, vite config alias @ → src

## Example

User: "Verify my webapp after UI changes"
→ Run preflight, start pnpm dev 3010, playwright navigate /, snapshot, console+network capture, resize mobile, generate HTML report, stop server, summarize pass/fail.
