#!/usr/bin/env python3
"""Generate visual HTML deepening report for arena-work."""
import pathlib, json, datetime
ROOT_BUILDER = pathlib.Path("/Users/villain/Projects/agent-arena-builder")
REPORT_DIR = ROOT_BUILDER / ".kilo" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
arch_json = REPORT_DIR / "architecture.json"
data={}
if arch_json.exists():
    data=json.loads(arch_json.read_text())

html = f"""<!doctype html><html><head><meta charset=utf-8><title>Agent Arena — Architecture Deepening</title>
<style>
:root{{--bg:#0A0A0A;--card:#111;--border:#222;--fg:#FAFAFA;--muted:#8A8F98;--accent:#3291FF}}
body{{background:var(--bg);color:var(--fg);font-family:Geist,system-ui,sans-serif;margin:0;padding:32px;max-width:1200px}}
h1{{font-size:28px;letter-spacing:-0.02em}} h2{{font-size:18px;margin-top:32px;color:var(--fg)}} .muted{{color:var(--muted);font-size:13px}}
.card{{border:1px solid var(--border);background:var(--card);border-radius:12px;padding:16px 20px;margin:12px 0}}
.badge{{display:inline-flex;border:1px solid var(--border);border-radius:6px;padding:2px 8px;font-size:11px;color:var(--muted)}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} @media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
pre{{background:#000;border:1px solid var(--border);border-radius:8px;padding:12px;overflow:auto;font-size:12px;line-height:1.5}}
a{{color:var(--accent)}}
</style></head><body>
<h1>Agent Arena — Architecture Deepening Report</h1>
<div class=muted>Generated {datetime.datetime.now().isoformat()} • Root arena-work</div>

<div class=grid>
<div class=card><div class=badge>HOTSPOT</div><h2>Backend — Executor Layer</h2>
<p>Executors share same base.run_battle phase loop. Shallow modules: arms_race, time_limited_siege duplicate run_phase scaffolding. Deepen by extracting <code>BattlePhaseOrchestrator</code> + <code>ToolSessionFactory</code>.</p>
<pre>Proposed seam:
- sandbox/executors/orchestrator.py: PhaseLoop(client, history, status_check)
- executors/formats/* keep only run_phase core logic
- base.py guard() + emit_result() stay</pre>
</div>
<div class=card><div class=badge>COUPLING</div><h2>Frontend — LiveBattle arts[]</h2>
<p>LiveBattle filters arts per render O(n*m). Connascence of position: model_ids[0] → builder assumption breakable for 3+ roles. Deepen by <code>useBattleModelMap</code> hook accumulating per model.</p>
<pre>interface: useBattleModelMap() => Map&lt;modelId, CodeArtifact[]&gt;
- append O(1)
- codeA = memo(map.get(modelA).join)
- removes filter in render</pre>
</div>
</div>

<div class=card><h2>Findings from scan</h2><pre>{json.dumps(data.get('summary',{}), indent=2)}</pre></div>

<div class=grid>
<div class=card><h2>Deepening Opportunities (priorities)</h2>
<ol>
<li><b>Export useBattleStream hook</b> — decouple SSE + reconnection from LiveBattle component; testable; location frontend/src/hooks/useBattleStream.ts</li>
<li><b>Executor Registry Self-Check</b> — seed_formats.py slug truncation collides; add validation script in backend/tests/test_executor_registry.py to assert unique slugs</li>
<li><b>Appwrite DB client singleton</b> — db.py get_databases creates new Client per request? Cache + retry with backoff</li>
<li><b>Auth интервал leak</b> — lib/auth.ts setInterval without clear on logout; move to useEffect with cleanup in SiteHeader or auth provider</li>
<li><b>FormatCard skeleton</b> — shallow UI component depending on format.* nullish; deepen props interface with discriminated union Loading vs Loaded</li>
<li><b>CORS + Vercel rewrites</b> — main.py allow_origins + regex duplicates; extract to config.py ALLOWED_ORIGINS, also add vercel.json headers validation</li>
</ol>
</div>
<div class=card><h2>What Good Looks Like</h2>
<ul>
<li>Backend: each executor < 200 LOC, one reason to change (phase definition), dependencies injected (client, guard)</li>
<li>Frontend: pages < 150 LOC, logic in hooks/lib, components pure</li>
<li>Shared: api.ts typed errors (ApiError) used consistently, no direct fetch outside</li>
<li>Docs: architecture-map.md keeps trust boundaries up to date (BYOK → crypto → Appwrite)</li>
</ul>
</div>
</div>

<div class=card><h2>Next Actions (tracer bullets)</h2>
<ol>
<li>Fix Home hardcoded 25 — replace with skeleton + real count fallback</li>
<li>Extract useBattleStream (de-risk LiveBattle)</li>
<li>Add executor registry test + orchestrator extraction</li>
<li>Harden auth interval cleanup</li>
<li>Run arena-security-audit + arena-ui-ux-review</li>
</ol>
</div>

</body></html>
"""
out = REPORT_DIR / "arch-deepening.html"
out.write_text(html)
print(f"Wrote {out}")
