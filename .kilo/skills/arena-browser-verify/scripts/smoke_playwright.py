#!/usr/bin/env python3
"""
Headless smoke via playwright if available, else fallback urllib.
Run: python scripts/smoke_playwright.py --url https://agent-arena-blond.vercel.app --local http://localhost:3010
"""
import argparse, sys, json, pathlib
try:
    from playwright.sync_api import sync_playwright
    HAS_PW=True
except: HAS_PW=False

def check_url(url: str):
    print(f"Checking {url}")
    if not HAS_PW:
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                body=r.read(5000).decode(errors='ignore')
                ok="Models fight" in body or "Agent Arena" in body
                print(f"Fallback fetch {r.status} ok={ok} len={len(body)}")
                return {"url": url, "status": r.status, "ok": ok}
        except Exception as e:
            print(f"Fetch failed {e}"); return {"url": url, "error": str(e)}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        console=[]
        page.on("console", lambda m: console.append(f"{m.type}:{m.text[:200]}"))
        errors=[]
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=8000)
            title=page.title()
            content=page.content()
            has_hero="Models fight" in content
            # check format library count via text
            # wait a bit for formats fetch
            page.wait_for_timeout(1500)
            content2=page.content()
            has_format_block="Format library" in content2
            format_0="Format library 0" in content2 or ">0<" not in content2 and "Loading formats" in content2
            result={"url":url,"title":title,"has_hero":has_hero,"has_format_block":has_format_block,"maybe_empty":format_0,"console":console[:20],"errors":errors,"ok":has_hero}
            print(json.dumps(result, indent=2))
            browser.close()
            return result
        except Exception as e:
            print(f"Playwright error {e}")
            browser.close()
            return {"url": url, "error": str(e)}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--url", default="https://agent-arena-blond.vercel.app")
    ap.add_argument("--local", default="http://localhost:3010")
    args=ap.parse_args()
    results=[]
    results.append(check_url(args.url))
    # try local if accessible
    try:
        results.append(check_url(args.local))
    except: pass
    out=pathlib.Path("/Users/villain/Projects/agent-arena-builder/.kilo/reports/browser-smoke.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Wrote {out}")
