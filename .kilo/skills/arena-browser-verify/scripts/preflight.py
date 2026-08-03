#!/usr/bin/env python3
import os, pathlib, json, urllib.request, urllib.error
ROOT_FRONT = pathlib.Path("/Users/villain/Projects/arena-work/frontend")
REPORT_DIR = pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

checks=[]
# env
env_file = ROOT_FRONT / ".env"
env_local = ROOT_FRONT / ".env.local"
for ef in [env_file, env_local, pathlib.Path("/Users/villain/Projects/agent-arena-builder/.env"), pathlib.Path("/Users/villain/Projects/agent-arena-builder/.env.local")]:
    if ef.exists():
        txt=ef.read_text()
        checks.append({"check": f"env file {ef.name} exists", "status": "ok", "detail": f"{len(txt.splitlines())} lines"})
        if "VITE_MODAL_URL" in txt:
            url = [l for l in txt.splitlines() if "VITE_MODAL_URL" in l][0]
            checks.append({"check": "VITE_MODAL_URL set", "status": "ok", "detail": url[:80]})
    else:
        checks.append({"check": f"env file {ef} missing", "status": "warn"})

# health
urls_to_check=[
    "https://aschenbrenerashton--agent-arena-backend-fastapi-app.modal.run/health",
    "https://agent-arena-blond.vercel.app",
]
for url in urls_to_check:
    try:
        req=urllib.request.Request(url, headers={"User-Agent":"arena-preflight"})
        with urllib.request.urlopen(req, timeout=5) as r:
            body=r.read(2000).decode(errors="ignore")
            checks.append({"check": f"GET {url}", "status": "ok" if r.status<400 else "fail", "code": r.status, "snippet": body[:200]})
    except Exception as e:
        checks.append({"check": f"GET {url}", "status": "fail", "error": str(e)[:200]})

out=REPORT_DIR/"preflight.json"
out.write_text(json.dumps(checks, indent=2))
md=["# Preflight", ""]
for c in checks:
    icon="✅" if c['status']=="ok" else "⚠️" if c['status']=="warn" else "❌"
    md.append(f"- {icon} {c['check']} — {c.get('detail','')}{c.get('code','')} {c.get('error','')} {c.get('snippet','')[:80]}")
(REPORT_DIR/"preflight.md").write_text("\n".join(md))
print(f"Wrote {out}")
