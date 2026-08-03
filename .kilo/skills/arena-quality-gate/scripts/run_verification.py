#!/usr/bin/env python3
import subprocess, pathlib, json, os
REPORT_DIR = pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def run(cmd, cwd, timeout=120):
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=False)
        return {"cmd": " ".join(cmd), "cwd": str(cwd), "returncode": proc.returncode, "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-3000:], "ok": proc.returncode==0}
    except Exception as e:
        return {"cmd": " ".join(cmd), "cwd": str(cwd), "returncode": 999, "error": str(e)[:500], "ok": False}

results={}
backend = pathlib.Path("/Users/villain/Projects/arena-work/backend")
frontend = pathlib.Path("/Users/villain/Projects/arena-work/frontend")

if backend.exists():
    results["pytest"] = run(["python", "-m", "pytest", "-q"], cwd=backend, timeout=90)
else:
    results["pytest"] = {"ok": False, "error": "backend not found"}

if frontend.exists():
    # check only if pnpm available
    results["typecheck"] = run(["pnpm", "run", "check"], cwd=frontend, timeout=60)
    results["lint"] = run(["pnpm", "run", "lint", "--silent"], cwd=frontend, timeout=60)
    results["build"] = run(["pnpm", "run", "build"], cwd=frontend, timeout=90)
else:
    results["frontend_missing"]=True

out_json=REPORT_DIR/"verification.json"
out_json.write_text(json.dumps(results, indent=2))
print(json.dumps({k: ("PASS" if v.get("ok") else "FAIL") for k,v in results.items()}, indent=2))
print(f"Wrote {out_json}")
