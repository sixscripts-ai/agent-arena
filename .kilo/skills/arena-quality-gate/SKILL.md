---
name: arena-quality-gate
description: Combined quality gate orchestrating all Agent Arena review skills. Runs architecture, security, UI/UX, performance, and browser verification in order, merges reports into single HTML dashboard, checks lint/typecheck/tests. Use when user says full review, audit all, quality gate, pre-deploy check, or wants complete improvement backlog for codebase + webapp. Triggers: full audit, quality gate, pre-deploy, review everything, improve my app.
---

# Arena Quality Gate — Full Review Orchestrator

Runs 5 specialist skills sequentially, aggregates, and produces master backlog.

## When to Use

- "Do full review of my codebase and webapp"
- Pre-deploy to https://agent-arena-blond.vercel.app
- After large refactor, before building new executor
- Need HTML dashboard of all findings

## Orchestration Workflow

### Step 0 - Load Specialist Skills

Ensure present:

- `arena-arch-review` (scan_architecture.py + deepening_report.py)
- `arena-security-audit` (security_scan.py)
- `arena-ui-ux-review` (ui_scan.py)
- `arena-perf-tune` (perf_scan.py)
- `arena-browser-verify` (preflight.py + smoke_playwright.py)

If any missing, run init.

### Step 1 - Execute Scans (parallelizable)

Run in order but can parallelize first 4 (no browser needed):

```bash
cd /Users/villain/Projects/agent-arena-builder
python .kilo/skills/arena-arch-review/scripts/scan_architecture.py
python .kilo/skills/arena-security-audit/scripts/security_scan.py
python .kilo/skills/arena-ui-ux-review/scripts/ui_scan.py
python .kilo/skills/arena-perf-tune/scripts/perf_scan.py
python .kilo/skills/arena-arch-review/scripts/deepening_report.py
python .kilo/skills/arena-browser-verify/scripts/preflight.py
python .kilo/skills/arena-browser-verify/scripts/smoke_playwright.py --url https://agent-arena-blond.vercel.app
```

Each writes to `.kilo/reports/`:

- architecture.json/md + arch-deepening.html
- security.json/md
- ui.json/md
- perf.json/md
- preflight.json/md + browser-smoke.json

### Step 2 - Verification Gates (Fail Fast)

Run project checks:

- Backend: `cd /Users/villain/Projects/arena-work/backend && pytest -q` (expect pass, but collect failures as findings)
- Frontend: `cd /Users/villain/Projects/arena-work/frontend && pnpm run check && pnpm run lint --silent && pnpm run build`
- If build fails -> HIGH severity finding in report.

Script `scripts/run_verification.py` does:

- Runs pytest captures output
- Runs pnpm check
- Returns JSON with pass/fail + tail logs

### Step 3 - Merge into Master Dashboard

Run `scripts/merge_reports.py` → `.kilo/reports/quality-gate.html`

Structure:

- Header: date, repo, live URL health, overall score (green/yellow/red)
- Section: Preflight (env + health)
- Section: Architecture (deepening + registry gaps)
- Section: Security (high first)
- Section: UI/UX (live bug Format library 0 highlighted)
- Section: Performance (hotspots)
- Section: Browser Smoke (screenshots via Playwright if available)
- Section: Verification Gates (pytest, typecheck, build)
- Backlog: sorted by severity * impact table with owner (backend/frontend/infra) and effort (S/M/L)

Impact calc:
- Security HIGH = critical
- UX bug causing 0 formats = critical (user sees broken)
- Perf HIGH in SSE or auth leak = high
- Arch large file = medium

### Step 4 - Propose Tickets

Generate `.kilo/plans/quality-gate-backlog.md` with:

```md
- [ ] [P0] Fix Home hardcoded formats.length || 25 hides empty (ui-ux)
- [ ] [P0] Ensure VITE_MODAL_URL set in Vercel + CORS (arch+ui)
- [ ] [P0] Sanitize check in executors + _resolve .. (security)
- [ ] [P1] Extract useBattleStream hook (perf+arch)
- [ ] [P1] Fix auth interval leak (perf)
- [ ] [P1] Make stream_battle async (perf)
- [ ] [P2] CodePane memo + rAF scroll (perf)
- [ ] [P2] Leaderboard pagination (perf)
```

### Step 5 - Execute (if user asks fix)

Pick P0/P1, implement per specialist skill guidance, re-run verification.

Additive-only rule for executors, but frontend hooks extraction allowed.

## Scripts

- `scripts/run_verification.py` — runs pytest + pnpm check/lint/build, captures logs
- `scripts/merge_reports.py` — merges 5 reports + verification into quality-gate.html
- `scripts/score.py` — computes overall health score 0-100

## References

- `references/rubric.md` — grading rubric for overall quality
- `references/ticket-template.md` — template for backlog items

## Validation

- `open .kilo/reports/quality-gate.html` shows sections, no broken links
- Verify at least 1 finding per category (if 0, maybe scan missed backend path)
- Run on clean clone `/Users/villain/Projects/arena-work` to ensure paths portable

## Example

User: "Run full quality gate for https://agent-arena-blond.vercel.app"
→ Execute 5 scans, run verification, merge into quality-gate.html, open browser, summarize P0 backlog, offer to fix.
