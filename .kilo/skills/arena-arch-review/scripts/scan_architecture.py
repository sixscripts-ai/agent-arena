#!/usr/bin/env python3
"""Deterministic architecture scanner for arena-work codebase."""
import ast, json, os, pathlib, re
from collections import defaultdict

ROOT_CANDIDATES = [
    "/Users/villain/Projects/arena-work",
    "/Users/villain/Projects/agent-arena-builder",
]
ROOT = next((p for p in ROOT_CANDIDATES if pathlib.Path(p).exists()), ".")

BACKEND = pathlib.Path(ROOT) / "backend" / "agent_arena"
FRONTEND = pathlib.Path(ROOT) / "frontend" / "src"
REPORT_DIR = pathlib.Path(ROOT_CANDIDATES[1]) / ".kilo" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def scan_py_file(p: pathlib.Path):
    try:
        txt = p.read_text()
    except: return {}
    issues=[]
    if len(txt.splitlines()) > 400:
        issues.append(f"Large file {len(txt.splitlines())} LOC")
    if txt.count("import") > 20:
        issues.append("High coupling: many imports")
    # check missing sanitize_artifact in executors
    if "executors" in str(p) and "client.round" in txt and "sanitize_artifact" not in txt and "redact" not in txt:
        # not all need, but many should
        if "executor" in p.name.lower():
            issues.append("Potential missing sanitize_artifact around client.round")
    # check Popen without killpg
    if "Popen" in txt and "start_new_session" not in txt:
        issues.append("Popen without start_new_session=True")
    if "ARENA_IN_SANDBOX" in txt and "==" not in txt:
        issues.append("ARENA_IN_SANDBOX check unusual")
    # check hardcoded secrets
    if re.search(r"sk-[a-zA-Z0-9]{20,}|ghp_[A-Za-z0-9]{20}", txt):
        issues.append("Possible hardcoded secret")
    # check bare except
    if "except:" in txt:
        issues.append("Bare except clause")
    # AST for deep nesting
    try:
        tree=ast.parse(txt)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While, ast.If)):
                depth=0
                cur=node
                # simplistic: count ancestors via manual recursion not needed; approximate by checking nested levels in text
                pass
    except: pass
    return {"file": str(p), "issues": issues, "loc": len(txt.splitlines())}

def scan_frontend_file(p: pathlib.Path):
    try:
        txt=p.read_text()
    except: return {}
    issues=[]
    if len(txt.splitlines())>350:
        issues.append(f"Large component {len(txt.splitlines())} LOC")
    if "fetch(" in txt and "api." not in txt and "lib/api.ts" not in str(p):
        issues.append("Direct fetch without api.ts wrapper")
    if "localStorage" in txt and "auth.ts" not in str(p) and "safeGet" not in txt:
        issues.append("Direct localStorage outside auth.ts-safeGet")
    if "dangerouslySetInnerHTML" in txt:
        issues.append("dangerouslySetInnerHTML usage")
    if re.search(r"formats\.length\s*\|\|\s*25", txt):
        issues.append("Hardcoded formats.length || 25 lie")
    if "slice(0,80)" in txt:
        issues.append("Silent truncation slice(0,80) without user hint")
    if "setInterval" in txt and "clearInterval" not in txt:
        # heuristic
        if "auth.ts" in str(p):
            issues.append("setInterval without cleanup in auth (potential leak)")
    if "console.log" in txt:
        issues.append("console.log left")
    return {"file": str(p), "issues": issues, "loc": len(txt.splitlines())}

def scan_executor_registry():
    issues=[]
    try:
        init_py = (BACKEND / "sandbox" / "executors" / "formats" / "__init__.py").read_text()
        seed_py = (BACKEND.parent / "seed_formats.py").read_text() if (BACKEND.parent / "seed_formats.py").exists() else ""
        # count registered executors
        reg_count = init_py.count("register(")
        # search seed_formats FORMAT list counting
        fmt_names = re.findall(r'"name"\s*:\s*"([^"]+)"', seed_py) if seed_py else []
        issues.append(f"Registry has {reg_count} register calls, seed has {len(fmt_names)} format name entries")
        if reg_count < 8:
            issues.append("Executor registry < expected (should be >=9 including advanced)")
    except Exception as e:
        issues.append(f"Registry scan failed: {e}")
    return issues

def main():
    report={"backend":[], "frontend":[], "registry": [], "summary": {}}
    if BACKEND.exists():
        for py in BACKEND.rglob("*.py"):
            if "node_modules" in str(py) or "__pycache__" in str(py): continue
            r=scan_py_file(py)
            if r.get("issues"): report["backend"].append(r)
    if FRONTEND.exists():
        for ext in ("*.tsx","*.ts"):
            for f in FRONTEND.rglob(ext):
                if "node_modules" in str(f): continue
                r=scan_frontend_file(f)
                if r.get("issues"): report["frontend"].append(r)
    report["registry"]=scan_executor_registry()
    total_issues = sum(len(x["issues"]) for x in report["backend"]) + sum(len(x["issues"]) for x in report["frontend"])
    report["summary"]={"total_py_issues": len(report["backend"]), "total_fe_issues": len(report["frontend"]), "total_findings": total_issues}
    out_json=REPORT_DIR/"architecture.json"
    out_md=REPORT_DIR/"architecture.md"
    out_json.write_text(json.dumps(report, indent=2))
    md_lines=["# Architecture Scan Report", f"Root: {ROOT}", f"Total findings: {total_issues}", "", "## Backend", ""]
    for b in report["backend"]:
        md_lines.append(f"- **{b['file']}** ({b['loc']} LOC)")
        for iss in b["issues"]: md_lines.append(f"  - {iss}")
    md_lines.extend(["", "## Frontend", ""])
    for f in report["frontend"]:
        md_lines.append(f"- **{f['file']}** ({f['loc']} LOC)")
        for iss in f["issues"]: md_lines.append(f"  - {iss}")
    md_lines.extend(["", "## Registry", ""])
    md_lines.extend([f"- {r}" for r in report["registry"]])
    out_md.write_text("\n".join(md_lines))
    print(f"Wrote {out_json} and {out_md} with {total_issues} findings")

if __name__=="__main__":
    main()
