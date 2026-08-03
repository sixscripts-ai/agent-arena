---
name: arena-arch-review
description: Deep architecture review for Agent Arena codebase. Scans backend executors, formats, battle lifecycle, frontend data flow, Appwrite/Modal integration, SSE streaming. Use when user asks to review codebase, improve architecture, find deepening opportunities, audit structure, check code quality, or wants HTML visual report. Triggers: review architecture, codebase audit, improve structure, deep module analysis, tech debt.
---

# Arena Architecture Review

Comprehensive codebase scanner purpose-built for `arena-work` (agent-arena backend + frontend) and `agent-arena-builder`.

## When to Use

- User says "review my codebase", "audit architecture", "improve structure"
- Before building new executor or UI feature
- After webapp shows issues like "formats loading 0" or SSE stalls
- For PR review: scan deepening opportunities, coupling, cohesion

## Workflow Decision Tree

```
Is request about whole codebase? → Full scan (backend + frontend + infra)
Is request about executors only? → Scan backend/agent_arena/sandbox/executors/
Is request about webapp only? → Scan frontend/src/pages, lib, components
Is request about specific file? → Deep dive that module + its dependencies
```

## Step 1 - Automated Scan

Use scripts/:

- `scripts/scan_architecture.py` — walks `backend/agent_arena/**/*.py`, `frontend/src/**/*.tsx`
  - Parses imports, detects cycles, large files (>400 LOC), deep nesting, duplicated logic
  - Checks executor registry completeness (`formats/__init__.py` vs `seed_formats.py`)
  - Checks frontend: missing error boundaries, direct fetch without api.ts, hardcoded URLs
  - Outputs `reports/architecture.json` + `.md`

- `scripts/deepening_report.py` — generates visual HTML report
  - Inspired by `improve-codebase-architecture` skill but tailored to arena
  - Shows: shallow modules, connascence, anti-patterns, suggested seams
  - Writes `reports/arch-deepening.html` (open in browser)

## Step 2 - Manual Deep Dive (Checklist)

### Backend Core (agent_arena/)

- [ ] `battles.py` — MAX_ACTIVE_BATTLES gate, _validate_model_ids, BackgroundTasks usage
- [ ] `formats.py` / `seed_formats.py` — slug collision, 25 formats claimed vs actual, engine diversity
- [ ] `sandbox/entrypoint.py` — ARENA_IN_SANDBOX gate, env var handling
- [ ] `sandbox/executors/base.py` — halted() deadline check, finish() judge error handling
- [ ] `sandbox/executors/formats/*` — each MUST have NAME, SLUG, Executor class, registered
- [ ] `event_bus.py` — durable vs ephemeral, ordering guarantees (created_at + event_id)
- [ ] `judge.py` — retry x3, clamping 0-100, redaction
- [ ] `auth.py` + `providers.py` — host: prefix bypass, ownership check
- [ ] `db.py` — Appwrite client singleton, failure modes
- [ ] `main.py` — CORS allow_origins vs regex, missing vercel.app subdomain coverage

### Frontend (arena-work/frontend/src)

- [ ] `lib/api.ts` — BASE URL fallback hardcoded to prod, error handling (ApiError.status)
- [ ] `lib/auth.ts` — safeGet/safeSet localStorage, JWT refresh interval leak, interval not cleared
- [ ] `pages/Home.tsx` — formats.length || 25 hardcoded lie, engines.length-1 assumption, loading state
- [ ] `pages/NewBattle.tsx` — selected state sync with providers, isHostProviderId allowed set, timeout input unbounded
- [ ] `pages/LiveBattle.tsx` — arts slice(-200) data loss, useMemo deps, AbortController cleanup, reconnect backoff
- [ ] `pages/Leaderboard.tsx` — overall format handling
- [ ] `components/CodePane.tsx` — lines.slice(0,80) truncates silently, code split "\n" no CR handling
- [ ] `hooks/useTheme.ts` — subscribeSystemTheme cleanup

### Infra

- [ ] `frontend/vercel.json` rewrite vs vercel routing
- [ ] `backend/pyproject.toml` deps pinned?
- [ ] `modal_entry.py` — FastAPI app export

## Step 3 - Improvement Proposal

For each finding, produce:

```md
### Finding: [TITLE] (Severity: high|med|low, Layer: backend|frontend|infra)
- Location: file:line
- Symptom: what user sees (e.g., "Format library 0" on prod)
- Root cause: code pattern
- Fix: concrete edit suggestion with snippet
- Test: how to verify (pytest, pnpm build, browser check)
```

Then grill with questions:
- What seam would make this module deep vs shallow?
- Where should interface boundary go?
- What's testable? What's AI-navigable?

## Step 4 - Execute Improvements (Additive-Only Where Possible)

- Backend: never edit existing format executors unless bug; new executors via additive files
- Frontend: extract hooks (useBattleStream), utils (roleMapping), error boundaries
- Always run `cd backend && pytest -q` and `cd frontend && pnpm run check && pnpm run build`

## Resources

- `references/architecture-map.md` — curated map of agent-arena layers, data flows, trust boundaries
- `references/deep-module-rules.md` — deep module vocabulary (interface, seam, connascence)
- `scripts/scan_architecture.py` — deterministic scan
- `scripts/deepening_report.py` — HTML report generator

## Examples

User: "Review my codebase and find why formats show 0 on vercel"
→ Run scan_architecture.py, check api.ts BASE fallback, formats.py public auth, CORS regex, Home.tsx engines Set logic, produce report, propose fix.

User: "Improve architecture before adding 25th format"
→ Scan registry gaps, propose shared BaseFormatExecutor, decouple judge weights, suggest seam in entrypoint for ARENA_IN_SANDBOX.
