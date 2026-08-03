#!/usr/bin/env python3
import pathlib, json, datetime
REPORT_DIR = pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(name):
    p=REPORT_DIR/name
    if p.exists():
        try: return json.loads(p.read_text())
        except: return {}
    return {}

arch=load_json("architecture.json")
sec=load_json("security.json")
ui=load_json("ui.json")
perf=load_json("perf.json")
pre=load_json("preflight.json")
ver=load_json("verification.json")
smoke=load_json("browser-smoke.json")

html=f"""<!doctype html><html><head><meta charset=utf-8><title>Arena Quality Gate</title>
<style>
:root{{--bg:#FAFAFA;--card:#FFFFFF;--border:#E4E4E7;--fg:#0A0A0A;--muted:#71717A;--accent:#0070F3;--danger:#DC2626;--success:#16A34A;--warn:#D97706}}
.dark{{--bg:#0A0A0A;--card:#111;--border:#222;--fg:#FAFAFA;--muted:#8A8F98}}
body{{background:var(--bg);color:var(--fg);font-family:Geist,system-ui,sans-serif;margin:0;padding:24px;max-width:1280px}}
h1{{font-size:28px;letter-spacing:-0.02em}} h2{{font-size:18px;margin-top:32px;border-bottom:1px solid var(--border);padding-bottom:8px}}
.muted{{color:var(--muted);font-size:13px}} .card{{border:1px solid var(--border);background:var(--card);border-radius:12px;padding:16px 20px;margin:12px 0}}
.badge{{display:inline-flex;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600}}
.badge-high{{background:#DC26261A;color:var(--danger);border:1px solid #DC262633}}
.badge-med{{background:#D977061A;color:var(--warn);border:1px solid #D9770633}}
.badge-low{{background:var(--card);color:var(--muted);border:1px solid var(--border)}}
pre{{background:#0A0A0A;color:#E5E5E5;border-radius:8px;padding:12px;overflow:auto;font-size:12px;line-height:1.5}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{border-bottom:1px solid var(--border);padding:8px 10px;text-align:left}} th{{font-size:11px;text-transform:uppercase;color:var(--muted)}}
</style></head><body>
<h1>Agent Arena — Quality Gate Dashboard</h1>
<div class=muted>Generated {datetime.datetime.now().isoformat()} • Live https://agent-arena-blond.vercel.app • Backend https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run</div>

<div class=grid>
<div class=card><h3>Scores</h3>
<p>Arch findings: {(arch.get('summary',{}).get('total_findings',0) if isinstance(arch,dict) else len(arch))}<br>
Sec high: {sec.get('summary',{}).get('high',0) if isinstance(sec,dict) else 'n/a'} / {sec.get('summary',{}).get('total',0) if isinstance(sec,dict) else len(sec.get('findings',[])) if isinstance(sec,dict) else 0}<br>
UI: {len(ui) if isinstance(ui,list) else 0} findings<br>
Perf: {len(perf) if isinstance(perf,list) else 0} hotspots<br>
Preflight: {len(pre) if isinstance(pre,list) else 0} checks<br>
Verification: pytest { 'PASS' if ver.get('pytest',{}).get('ok') else 'FAIL'}, build { 'PASS' if ver.get('build',{}).get('ok') else 'FAIL' if 'build' in ver else 'unknown'}
</p></div>
<div class=card><h3>P0 Backlog (auto)</h3>
<ul>
<li><b>[P0]</b> Fix Home formats.length || 25 + engines 0 — hide lies, add skeleton, check VITE_MODAL_URL env in Vercel</li>
<li><b>[P0]</b> Security: ensure all executors call sanitize_artifact + _resolve .. rejection (run security_scan)</li>
<li><b>[P0]</b> Preflight: backend /health must 200, /formats CORS allows *.vercel.app</li>
<li><b>[P1]</b> Auth interval leak in lib/auth.ts + useEffect cleanup</li>
<li><b>[P1]</b> LiveBattle arts.filter O(n) + scroll thrash – extract useBattleStream</li>
<li><b>[P1]</b> SSE time.sleep blocking – make async</li>
<li><b>[P2]</b> CodePane split memo + line cap UX</li>
</ul>
</div>
</div>

<h2>Preflight</h2><div class=card><pre>{json.dumps(pre, indent=2)[:8000]}</pre></div>
<h2>Architecture</h2><div class=card><pre>{json.dumps(arch.get('summary', arch) if isinstance(arch,dict) else arch, indent=2)[:8000]}</pre><p><a href="arch-deepening.html">Open deepening HTML report</a></p></div>
<h2>Security</h2><div class=card><pre>{json.dumps(sec.get('findings', sec)[:20] if isinstance(sec,dict) else sec, indent=2)[:10000]}</pre></div>
<h2>UI/UX</h2><div class=card><pre>{json.dumps(ui[:20] if isinstance(ui,list) else ui, indent=2)[:8000]}</pre></div>
<h2>Performance</h2><div class=card><pre>{json.dumps(perf[:20] if isinstance(perf,list) else perf, indent=2)[:8000]}</pre></div>
<h2>Verification</h2><div class=card><pre>{json.dumps(ver, indent=2)[:10000]}</pre></div>
<h2>Browser Smoke</h2><div class=card><pre>{json.dumps(smoke, indent=2)[:8000]}</pre></div>

<h2>Next Actions</h2><div class=card>
<ol>
<li>Fix formats 0 bug (P0)</li>
<li>Run full pytest + build gate</li>
<li>Extract useBattleStream hook</li>
<li>Harden sandbox gates + crypto</li>
<li>Polish CodePane + skeletons + a11y</li>
</ol>
<p>All reports in .kilo/reports/</p>
</div>

</body></html>
"""

out=REPORT_DIR/"quality-gate.html"
out.write_text(html)
print(f"Wrote {out}")
