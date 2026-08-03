#!/usr/bin/env python3
import re, json, pathlib
ROOTS = ["/Users/villain/Projects/arena-work", "/Users/villain/Projects/agent-arena-builder"]
BACKEND = pathlib.Path(ROOTS[0]) / "backend"
FRONTEND = pathlib.Path(ROOTS[0]) / "frontend" / "src"
REPORT_DIR = pathlib.Path(ROOTS[1]) / ".kilo" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

patterns = [
    (r"sk-[A-Za-z0-9]{20,}", "HIGH", "Possible OpenAI key"),
    (r"ghp_[A-Za-z0-9]{20,}", "HIGH", "GitHub token"),
    (r"api_key.*=.*['\"][A-Za-z0-9]{20,}", "MEDIUM", "Hardcoded api_key assignment"),
    (r"ENCRYPTION_KEY.*=.*['\"]", "HIGH", "Hardcoded ENCRYPTION_KEY"),
    (r"console\.log\(.*key.*\)", "MEDIUM", "Console log of key"),
    (r"dangerouslySetInnerHTML", "HIGH", "XSS via dangerouslySetInnerHTML"),
    (r"Popen.*shell\s*=\s*True", "HIGH", "Shell True in Popen"),
    (r"except:\s*$", "LOW", "Bare except"),
    (r"allow_origins.*\*", "MEDIUM", "Wildcard CORS?"),
]

def grep_file(p: pathlib.Path):
    findings=[]
    try:
        txt=p.read_text()
    except: return findings
    for pat, sev, desc in patterns:
        for m in re.finditer(pat, txt, re.IGNORECASE|re.MULTILINE):
            # skip if in test or example
            if "test_" in str(p) or "example" in str(p): continue
            line_no = txt[:m.start()].count("\n")+1
            findings.append({"file": str(p), "line": line_no, "severity": sev, "desc": desc, "match": m.group(0)[:120]})
    # bespoke checks
    if "executors" in str(p) and "client.round" in txt:
        if "sanitize_artifact" not in txt and "_harness" not in str(p) and "base.py" not in str(p):
            findings.append({"file": str(p), "line": 1, "severity": "MEDIUM", "desc": "client.round without sanitize_artifact?", "match": "client.round usage"})
    if "_resolve" in txt or "ToolSession" in txt:
        if '".."' not in txt and "'..'" not in txt:
            findings.append({"file": str(p), "line": 1, "severity": "HIGH", "desc": "ToolSession missing .. rejection", "match": "_resolve check"})
    if "base_url" in txt and "health" in str(p).lower():
        if "169.254" not in txt and "allowlist" not in txt.lower():
            findings.append({"file": str(p), "line": 1, "severity": "MEDIUM", "desc": "Provider base_url SSRF potential – health endpoint user-controlled", "match": "base_url"})
    return findings

all_findings=[]
for root in [BACKEND, FRONTEND]:
    if not root.exists(): continue
    for ext in ["*.py", "*.ts", "*.tsx"]:
        for f in root.rglob(ext):
            if "node_modules" in str(f) or ".pyc" in str(f): continue
            all_findings.extend(grep_file(f))

# critical file list
critical_checks=[]
# check crypto.py uses Fernet
try:
    cpath = BACKEND / "agent_arena" / "crypto.py"
    if cpath.exists():
        txt=cpath.read_text()
        if "Fernet" not in txt: critical_checks.append({"check":"crypto Fernet missing", "severity":"HIGH"})
        if "ENCRYPTION_KEY" not in txt: critical_checks.append({"check":"ENCRYPTION_KEY env not used", "severity":"MEDIUM"})
except: pass
# check battles _get_owned
try:
    bpath = BACKEND / "agent_arena" / "battles.py"
    txt=bpath.read_text()
    required=["_get_owned", "_validate_model_ids", "MAX_ACTIVE_BATTLES"]
    for r in required:
        if r not in txt: critical_checks.append({"check": f"battles.py missing {r}", "severity":"MEDIUM"})
except: pass

report={"findings": all_findings, "critical": critical_checks, "summary": {"total": len(all_findings), "high": len([x for x in all_findings if x['severity']=='HIGH'])}}
out_json=REPORT_DIR/"security.json"
out_json.write_text(json.dumps(report, indent=2))
# md
md=["# Security Scan", f"Total {len(all_findings)} findings, High: {report['summary']['high']}", ""]
for f in sorted(all_findings, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(x['severity'],3)):
    md.append(f"- [{f['severity']}] {f['desc']} — {f['file']}:{f['line']} → `{f['match']}`")
if critical_checks:
    md.append("\n## Critical Checks")
    for c in critical_checks: md.append(f"- [{c['severity']}] {c['check']}")
(REPORT_DIR/"security.md").write_text("\n".join(md))
print(f"Wrote {out_json} with {len(all_findings)} findings")
