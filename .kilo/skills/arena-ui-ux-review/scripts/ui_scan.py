#!/usr/bin/env python3
import pathlib, json, re
ROOT = pathlib.Path("/Users/villain/Projects/arena-work/frontend/src")
REPORT_DIR = pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

findings=[]
for f in ROOT.rglob("*.tsx"):
    txt=f.read_text()
    if "Loading formats" in txt and "skeleton" not in txt.lower():
        findings.append({"file": str(f), "type":"loading", "msg":"Raw 'Loading...' text without skeleton", "severity":"medium"})
    if re.search(r"formats\.length\s*\|\|\s*25", txt):
        findings.append({"file": str(f), "type":"hardcode", "msg":"Hardcoded fallback 25 hides empty state bug", "severity":"high"})
    if 'text-[11px]' in txt:
        # count occurrences
        cnt = txt.count('text-[11px]')
        if cnt>5:
            findings.append({"file": str(f), "type":"a11y", "msg":f"{cnt}x text-[11px] may fail WCAG readable min", "severity":"low"})
    if "aria-label" not in txt and "<button" in txt:
        # heuristic: if button with only icon
        if "☰" in txt or "h-8 w-8 place-items" in txt:
            findings.append({"file": str(f), "type":"a11y", "msg":"Button may lack aria-label (mobile menu)", "severity":"medium"})
    if "col-span-12" in txt and "sm:" not in txt and "md:" not in txt:
        # already has md? check simpler
        pass
    if "slice(0,80)" in txt:
        findings.append({"file": str(f), "type":"ux", "msg":"Truncates lines slice(0,80) silently – show +N hidden", "severity":"medium"})
    if "format_id" in txt and "img" in txt.lower():
        findings.append({"file": str(f), "type":"perf", "msg":"Check image usage", "severity":"low"})
    if "setInterval" in txt and "clearInterval" not in txt:
        findings.append({"file": str(f), "type":"perf", "msg":"setInterval without cleanup", "severity":"high"})
    if "console.log" in txt:
        findings.append({"file": str(f), "type":"hygiene", "msg":"console.log leftover", "severity":"low"})

# check index.css tokens
index_css = pathlib.Path("/Users/villain/Projects/arena-work/frontend/src/index.css")
if index_css.exists():
    css=index_css.read_text()
    # contrast checks
    if "#71717A" in css:
        findings.append({"file": str(index_css), "type":"contrast", "msg":"--fg-muted #71717A on white may fail AA (ratio ~4.0)", "severity":"medium"})
    if "@import url('https://fonts.googleapis.com" in css:
        findings.append({"file": str(index_css), "type":"perf", "msg":"Google fonts @import blocking – should preconnect link in index.html", "severity":"low"})

out_json=REPORT_DIR/"ui.json"
out_json.write_text(json.dumps(findings, indent=2))
md=["# UI Scan", f"{len(findings)} findings", ""]
for f in findings:
    md.append(f"- [{f['severity']}] {f['type']} — {f['msg']} @ {f['file']}")
(REPORT_DIR/"ui.md").write_text("\n".join(md))
print(f"Wrote {out_json} with {len(findings)} findings")
