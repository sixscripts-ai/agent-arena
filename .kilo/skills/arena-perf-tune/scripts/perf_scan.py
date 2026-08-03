#!/usr/bin/env python3
import pathlib, json, re
FRONT = pathlib.Path("/Users/villain/Projects/arena-work/frontend/src")
BACK = pathlib.Path("/Users/villain/Projects/arena-work/backend/agent_arena")
REPORT_DIR = pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

findings=[]
# frontend perf
for f in FRONT.rglob("*.tsx"):
    txt=f.read_text()
    if "arts.filter" in txt and "useMemo" not in txt:
        # but we know LiveBattle uses useMemo but still O(n) per map
        findings.append({"file": str(f), "area":"react", "msg":"arts.filter in render path – O(n) per render, use Map accumulator", "severity":"high"})
    if "split(\"\\n\")" in txt and "CodePane" in str(f):
        findings.append({"file": str(f), "area":"react", "msg":"code.split('\\n') each render – memoize", "severity":"medium"})
    if "scrollIntoView" in txt and "requestAnimationFrame" not in txt:
        findings.append({"file": str(f), "area":"react", "msg":"scrollIntoView smooth on every arts change – thrash, debounce via rAF", "severity":"medium"})
    if txt.count("useMemo")>5:
        findings.append({"file": str(f), "area":"react", "msg":"Many useMemo – verify deps stable", "severity":"low"})
    if "import.*lucide-react" in txt and "{" not in txt.split("lucide-react")[0][-80:] if "lucide-react" in txt else False:
        pass
    if "React.lazy" not in txt and ("DesignOptions" in txt or "DesignMockup" in txt):
        findings.append({"file": str(f), "area":"bundle", "msg":"Heavy route without lazy – add React.lazy", "severity":"medium"})

for f in FRONT.rglob("*.ts"):
    txt=f.read_text()
    if "setInterval" in txt and "clearInterval" not in txt and "useEffect" in txt:
        findings.append({"file": str(f), "area":"leak", "msg":"setInterval without cleanup – interval leak", "severity":"high"})
    if "fetch(" in txt and "AbortController" not in txt:
        findings.append({"file": str(f), "area":"network", "msg":"fetch without AbortController – no cancel", "severity":"low"})

# backend perf
for f in BACK.rglob("*.py"):
    txt=f.read_text()
    if "time.sleep(1)" in txt and "stream" in str(f):
        findings.append({"file": str(f), "area":"sse", "msg":"Blocking time.sleep(1) in SSE generator – should be async or use asyncio.sleep", "severity":"high"})
    if "sorted(" in txt and "event_bus" in txt or "sorted(" in txt and "subscribe" in txt:
        findings.append({"file": str(f), "area":"sse", "msg":"sorted() each loop for event ordering – cache or insertion sort", "severity":"medium"})
    if "list_documents" in txt and "limit(100)" in txt:
        # many files use 100
        if "active_battle_count" in txt or "list_battles" in txt:
            findings.append({"file": str(f), "area":"db", "msg":"list_documents limit 100 where MAX 5 or pagination needed", "severity":"low"})
    if "def event_generator" in txt and "async def" not in txt:
        findings.append({"file": str(f), "area":"sse", "msg":"Sync event_generator blocks runner – consider async", "severity":"medium"})

out=REPORT_DIR/"perf.json"
out.write_text(json.dumps(findings, indent=2))
md=["# Perf Scan", f"{len(findings)} findings", ""]
for f in findings:
    md.append(f"- [{f['severity']}] {f['area']} — {f['msg']} @ {f['file']}")
(REPORT_DIR/"perf.md").write_text("\n".join(md))
print(f"Wrote {out} with {len(findings)} findings")
