---
name: arena-perf-tune
description: Performance tuning for Agent Arena backend and frontend. Audits bundle size, Vite build, SSE streaming efficiency, Modal sandbox cold starts, Appwrite query limits, React render counts, token/s streaming. Use when user wants performance improvements, faster battles, lower latency, bundle optimization, or frontend lag. Triggers: perf audit, optimize, slow battle, bundle size, streaming lag, latency.
---

# Arena Perf Tune

Performance specialist for arena-work: FastAPI on Modal + Appwrite + React SSE dual code streaming.

## When to Use

- "Optimize performance", "battles slow", "frontend laggy"
- SSE artifacts lag, CodePane 80 line slice causes jank, LiveBattle re-renders
- Modal cold start patience, Appwrite Query.limit(100) overhead
- Build size large, Vite chunks

## Diagnostics

### Backend

- `main.py` CORS regex `https://.*\.vercel\.app` — PCRE overhead minor but check pre-compile
- `battles.py` `stream_battle` event_generator:
  - `event_bus.load_durable` loads all history then seen_ids dedup — O(n) each reconnect
  - `subscribe` every 1s sleep loop — polling vs pubsub? Modal memory vs Appwrite realtime
  - sorted() by created_at+event_id every loop — expensive if 200 events
  - time.sleep(1) blocking in generator? EventSourceResponse runs sync — should use async?
- `sandbox_launcher.py` — Modal sandbox spawn time, env vars size
- `executors/base.py` — run_battle loops phases, client.round per phase — batch?
- `judge.py` — host judge Kimi-K3 retry x3 adds latency, judge runs after history full — streaming judge progress ideal
- Appwrite: list_documents with limit 100 but no pagination, active_battle_count counts up to 100 even though MAX 5

### Frontend

- `App.tsx` Bundle: react-router-dom 7.3, lucide-react tree shaking? Import all icons?
- `lib/api.ts` streamBattle: reader.read() loop splits "\n" but buffer.pop() can leak, TextDecoder stream true correct but no handling of SSE retry field
- `LiveBattle.tsx`:
  - `arts` array grows to 200 slice but filter each render for codeA/codeB O(n) Map? Use memo per model_id
  - bottomRef scrollIntoView smooth on every arts change — layout thrash
  - status in deps triggers reconnect loop reconnect on status change
  - No virtualization for event stream list
- `Home.tsx` formats Fetch: cancelled flag correct but no AbortController, no staleTime
- `CodePane.tsx` lines = code.split("\n") each render — heavy for large code, memoize, line numbers 80 cap hides but still splits entire string
- `useAuth` setInterval 10min refresh without cleanup on unmount — interval leak if init called multiple times (SiteHeader useEffect init dep -> runs each nav?)
- Index.css @import Google fonts blocking — should preconnect

## Automated Scan

`scripts/perf_scan.py`:

- Analyzes frontend: reads vite.config.ts, checks manualChunks, tailwind purge, lucide tree-shake
- Measures backend: times event_bus sorted, counts db queries per request (grep list_documents), detects blocking sleep
- Checks React: useMemo missing deps, array.filter in render, string concat inside render
- Outputs `reports/perf.json` with hotspots

`scripts/bundle_report.py`:

- Runs `pnpm run build` and parses dist stats (assets size), suggests splitting FormatCard, CodePane dynamic import
- Suggests vite-plugin: vite bundle analyzer

## Optimization Plays

### Frontend (Vercel guidelines)

- **React perf:**
  - Memoize CodePane lines, extract LineNumbers component memoized
  - Use `useDeferredValue` for code streaming to avoid blocking UI
  - Replace arts.filter(...).map(...).join("\n\n") with per-model accumulator (useRef Map)
  - Debounce scrollIntoView (requestAnimationFrame)
  - Cleanup auth interval in useEffect return
  - Add React.lazy for DesignOptions, DesignMockup (heavy mockup routes)

- **Network:**
  - api.ts BASE: replace hardcoded prod URL with env + fallback only dev, show banner if env missing
  - Add stale-while-revalidate for formats (SWR cache 60s)
  - SSE: handle reconnect with Last-Event-ID if available (event_bus stores)

- **Build:**
  - vite.config.ts: split vendor (react, router, zustand), add manualChunks
  - Preconnect fonts: <link rel=preconnect> for fonts.googleapis
  - Tailwind: check content globs cover all src

### Backend (Modal + SSE)

- Make stream_battle async generator: `async def event_generator()`, use asyncio.sleep, allow concurrent
- Cache durable load after first snapshot, only poll new events after checkpoint
- Reduce sorted() to insertion sort or maintain ordered index by created_at
- Appwrite queries: add index on user_id+status+created_at, reduce limit to 20 where 100 not needed
- Sandbox: Modal image caching, warm pool, avoid sequential phases if isolated
- Judge: stream judge tokens instead of blocking finish()?

### Overlooked but impactful

- Home `formats.length || 25` causes hydration mismatch if SSR? Vite SPA no SSR but still UX lie
- apis/api.ts request() reads text then JSON.parse — should handle empty, but adds copy; use res.json() with guard
- Leaders leaderboard: no pagination, fetch all rows — add limit + elo descending index

## Workflow

1. Run `perf_scan.py` → report
2. Pick top 3 bottlenecks (severity * user impact)
3. Implement fix with before/after measurement:
   - Frontend: `pnpm build` size diff, Chrome perf trace note
   - Backend: simulated SSE load test (curl stream)
   - Explain tradeoff (e.g., caching durable increases memory but cuts Appwrite reads)
4. Verify `pytest -q` still passes, frontend check/build passes, manual browser smoke

## Resources

- `references/perf-hotspots.md` — known arena hotspots (SSE polling, auth interval leak)
- `references/react-perf-patterns.md` — memo, deferred, lazy for this codebase
- `references/modal-coldstart.md` — Modal container keep-warm strategies
- `scripts/perf_scan.py` — grep + AST perf detector
- `scripts/bundle_report.py` — build size analyzer

## Metrics to Track

- FE: bundle total < 250kb gz, LCP < 2.5s, Format load p95 < 800ms, CodePane render < 16ms
- BE: SSE first event p95 < 2s, durable load < 200ms, battle create < 500ms, active count query < 100ms
- E2E: Time to first artifact token from Start click < 5s (includes Modal spawn)

## Example

User: "My webapp feels laggy during battles"
→ Run perf_scan, identify arts.filter O(n) per render + scrollIntoView thrash + auth interval leak, fix with per-model map + raf debounce + cleanup, measure CodePane render, push build size check.
