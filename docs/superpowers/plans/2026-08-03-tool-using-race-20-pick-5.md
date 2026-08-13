# Tool-using race 20 pick 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement agent_tool_race engine where agents choose 5 of 20 skills, produce file-tree workspace with THEORY.md and usable asset, with mem0 + Elo self-learning, fixing copy-paste code look.

**Architecture:** Add AdvancedExecutor with ToolSession (filesystem+python exec+test runner, Popen killpg, sandbox gate ARENA_IN_SANDBOX), parse strict TOOL lines, emit structured files JSON, seed new format Tool-using coding race (target is_palindrome kata), update CodePane to parse files tree and chosen_skills chips, store winning combos in mem0 and extend leaderboard for skill Elo.

**Tech Stack:** FastAPI, Modal Sandbox, Appwrite, React Vite, Zustand, mem0 API, Python ToolSession, Popen killpg, pnpm

## Global Constraints
- Keep 14 existing formats + add 15th Tool-using coding race (additive-only, never delete existing)
- .kilo/ runtime ignored: .kilo/node_modules/, memory.json, mem0/, plans/, reports/, package-lock.json
- Always sanitize_artifact before client.round
- Reject .. path traversal in ToolSession _resolve
- Max 6 tool turns, 14 steps, 20s tool_timeout, 240s exec_timeout
- Frontend must keep backward compat: if artifact is string (old executors) show as before, if JSON with files parse file tree
- Skill pool 20 curated by user from .kilo/skills/* + custom_skills/, pick exactly 5 per battle, THEORY.md required

---

### Task 1: Advanced executor toolbelt parser

**Files:**
- Create: `backend/agent_arena/sandbox/executors/advanced_executor.py`
- Test: `backend/tests/test_advanced_executor.py`

**Interfaces:**
- Consumes: base.Executor, client.InternalClient, _harness.model_code/run_python/write_assets
- Produces: AdvancedExecutor class with methods parse_tool_calls(text)->list[dict], run_phase, run_battle, and ToolSession class

- [ ] **Step 1: Write failing test for parser**

```python
# backend/tests/test_advanced_executor.py
from agent_arena.sandbox.executors.advanced_executor import parse_tool_calls

def test_parse_tool_calls_single_line():
    calls = parse_tool_calls("TOOL ls path=work\nTOOL read path=sandbox.py\nDONE")
    assert calls[0]["tool"] == "ls"
    assert calls[0]["path"] == "work"
    assert calls[1]["tool"] == "read"
    assert calls[2]["tool"] == "done"

def test_parse_tool_calls_block():
    text = "TOOL write path=solution.py\nprint('hi')\nEND_TOOL\nDONE"
    calls = parse_tool_calls(text)
    assert calls[0]["tool"] == "write"
    assert calls[0]["content"] == "print('hi')"
```

- [ ] **Step 2: Run test to fail**

Run: `.venv/bin/python -m pytest backend/tests/test_advanced_executor.py::test_parse_tool_calls_single_line -v`
Expected: FAIL ModuleNotFoundError advanced_executor

- [ ] **Step 3: Implement minimal parser + ToolSession scaffold**

```python
# backend/agent_arena/sandbox/executors/advanced_executor.py
from __future__ import annotations
import os, subprocess, tempfile, signal
from pathlib import Path

def parse_tool_calls(text: str) -> list[dict]:
    calls = []
    lines = text.splitlines()
    i=0
    while i < len(lines):
        line=lines[i].strip()
        if not line:
            i+=1; continue
        if line.startswith("TOOL "):
            parts = line[5:].split()
            tool = parts[0]
            args={}
            content=None
            # single-line tools
            if tool in ("read","ls","test","clean"):
                for p in parts[1:]:
                    if "=" in p:
                        k,v=p.split("=",1)
                        args[k]=v
                calls.append({"tool":tool, **args})
            elif tool in ("write","run"):
                # block until END_TOOL
                path=None
                for p in parts[1:]:
                    if p.startswith("path="):
                        path=p.split("=",1)[1]
                content_lines=[]
                i+=1
                while i < len(lines) and lines[i].strip()!="END_TOOL":
                    content_lines.append(lines[i])
                    i+=1
                calls.append({"tool":tool,"path":path,"content":"\n".join(content_lines)})
            elif tool=="DONE":
                calls.append({"tool":"done"})
            else:
                calls.append({"tool":"error","message":f"unknown {tool}"})
        i+=1
    return calls

class ToolSession:
    def __init__(self, root: Path):
        self.root=root
        self.root.mkdir(parents=True, exist_ok=True)
    def _resolve(self, rel: str) -> Path:
        p=(self.root/rel).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("path outside workdir")
        if ".." in rel:
            raise ValueError(".. rejected")
        return p
```

- [ ] **Step 4: Run test pass**

Run: `.venv/bin/python -m pytest backend/tests/test_advanced_executor.py -v`
Expected: PASS for 2 parser tests (others may fail, ok)

- [ ] **Step 5: Commit**

```bash
git add backend/agent_arena/sandbox/executors/advanced_executor.py backend/tests/test_advanced_executor.py
git commit -m "feat(executor): scaffold advanced toolbelt parser + ToolSession"
```

### Task 2: ToolSession run/test/write with killpg + sandbox gate

**Files:**
- Modify: `backend/agent_arena/sandbox/executors/advanced_executor.py`
- Test: `backend/tests/test_advanced_executor.py`

**Interfaces:**
- Consumes: subprocess.Popen, signal, tempfile
- Produces: ToolSession.write/read/ls/clean/run/test methods, validate gate

- [ ] **Step 1: Write failing test for ToolSession security and run timeout**

```python
def test_tool_session_reject_dotdot(tmp_path):
    from agent_arena.sandbox.executors.advanced_executor import ToolSession
    sess = ToolSession(tmp_path / "work")
    try:
        sess._resolve("../../etc/passwd")
        assert False
    except ValueError:
        assert True

def test_tool_session_run_timeout(tmp_path):
    from agent_arena.sandbox.executors.advanced_executor import ToolSession
    sess = ToolSession(tmp_path / "work")
    sess.write("loop.py", "while True: pass")
    out, err, rc = sess.run("loop.py", timeout=1)
    assert "timeout" in err.lower() or rc==-1
```

- [ ] **Step 2: Run fail**

Run: `.venv/bin/python -m pytest backend/tests/test_advanced_executor.py::test_tool_session_reject_dotdot -v`
Expected: FAIL not implemented

- [ ] **Step 3: Implement run/test/write etc**

```python
def write(self, rel, content):
    p=self._resolve(rel); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content)
def read(self, rel):
    return self._resolve(rel).read_text()
def ls(self, rel="."):
    p=self._resolve(rel); return [x.name for x in p.iterdir()] if p.is_dir() else []
def clean(self, rel):
    import shutil; p=self._resolve(rel); shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
def run(self, rel, timeout=20):
    p=self._resolve(rel)
    proc=subprocess.Popen(["python3", str(p)], cwd=str(self.root), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        return out[:50000], err[:20000], proc.returncode
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        return "", f"timeout after {timeout}s", -1
def test(self, rel, timeout=20):
    out, err, rc = self.run(rel, timeout)
    passed="TEST_PASS" in out
    return {"passed":passed, "out":out, "err":err, "rc":rc}
```

Add gate check at top of run_phase:

```python
if os.environ.get("ARENA_IN_SANDBOX")!="1":
    raise RuntimeError("must run inside sandbox")
```

- [ ] **Step 4: Run pass**

Run: `.venv/bin/python -m pytest backend/tests/test_advanced_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agent_arena/sandbox/executors/advanced_executor.py backend/tests/test_advanced_executor.py
git commit -m "feat(executor): ToolSession run/test/write with killpg + dotdot rejection + sandbox gate"
```

### Task 3: AdvancedExecutor run_phase + run_battle full loop

**Files:**
- Modify: `backend/agent_arena/sandbox/executors/advanced_executor.py`
- Test: `backend/tests/test_advanced_executor.py`

- [ ] **Step 1: Write failing test for full battle via FakeTransport**

```python
def test_advanced_full_loop():
    from agent_arena.sandbox.executors.advanced_executor import AdvancedExecutor
    from agent_arena.sandbox.client import FakeTransport, InternalClient
    transport=FakeTransport()
    transport.model_replies={"player_a":"TOOL write path=solution.py\ndef is_palindrome(s): return s==s[::-1]\nEND_TOOL\nTOOL test path=solution.py\nEND_TOOL\nDONE"}
    transport.judge_result={"scores":{"player_a":80,"player_b":20},"justifications":{"player_a":"ok","player_b":"no"},"judge_model":"mock"}
    client=InternalClient(transport)
    ex=AdvancedExecutor()
    scores=ex.run_battle(battle_id="b", format_config={"name":"Tool-using coding race","engine":"agent_tool_race","roles":["player_a","player_b","judge"],"phases":[{"name":"race","participants":["player_a","player_b"]}],"target_code":"def is_palindrome(s): return False","max_tool_turns":2,"max_tool_steps":6}, model_ids=["player_a","player_b"], round_visibility="open", timeout_seconds=60, role_to_model={"player_a":"player_a","player_b":"player_b"}, client=client)
    assert scores["player_a"]==80
```

- [ ] **Step 2: Run fail**, **Step 3: Implement run_phase loop handling SKILLS + THEORY + files JSON**

Implementation must: loop max_tool_turns, per turn call client.model with system prompt listing 20 skills (from env or hardcoded), parse TOOL calls, execute via ToolSession, emit artifact via client.round, track steps, on DONE emit EXECUTOR_RESULT json with files via ls + read.

- [ ] **Step 4: Run pass**, **Step 5: Commit**

### Task 4: Seed formats + registry + entrypoint

**Files:**
- Modify: `backend/agent_arena/seed_formats.py`, `backend/agent_arena/sandbox/executors/__init__.py`, `backend/agent_arena/sandbox/executors/formats/__init__.py`, `backend/agent_arena/sandbox/entrypoint.py`, `backend/agent_arena/config.py` maybe
- Create: `backend/agent_arena/sandbox/executors/formats/advanced.py`

**Interfaces:**

- [ ] **Step 1: Create advanced.py from template**

```python
from ..advanced_executor import AdvancedExecutor
NAME="Tool-using coding race"
SLUG="tool-using-coding-race"
class ToolUsingCodingRaceExecutor(AdvancedExecutor):
    pass
```

- [ ] **Step 2: Patch __init__.py add agent_tool_race engine**

```python
from .advanced_executor import AdvancedExecutor
_ENGINE_REGISTRY["agent_tool_race"]=AdvancedExecutor
```

- [ ] **Step 3: Patch formats/__init__.py from . import advanced**

- [ ] **Step 4: Patch seed_formats.py additive: ENGINE_TEMPLATES agent_tool_race, RUBRICS, FORMAT_DEFINITIONS append, FORMAT_EXTRA**

Copy from .kilo/skills/advanced-builder/assets/format_extra_template.json and resources/engine_template.json

- [ ] **Step 5: Patch entrypoint.py set ARENA_IN_SANDBOX=1**

- [ ] **Step 6: Test get_executor resolves tool-using-coding-race**

Run: `.venv/bin/python -m pytest backend/tests/test_executor_registry.py -v`

- [ ] **Step 7: Commit**

### Task 5: Frontend CodePane file-tree + chosen skills

**Files:**
- Modify: `frontend/src/components/CodePane.tsx`, `frontend/src/pages/LiveBattle.tsx`

- [ ] **Step 1: Write failing test? Frontend no test, manual check: CodePane should parse files JSON**

Implement: if code starts with { and contains "files", JSON.parse, else fallback old string.

```tsx
type FileMap = Record<string,string>
function parseFiles(code: string): {files:FileMap, meta:any} | null {
 try { const j=JSON.parse(code); if(j.files) return j; } catch {} return null
}
```

Render left tree: Object.keys(files).map + selected file viewer.

- [ ] **Step 2: Build frontend**

Run: `cd frontend && pnpm build`

Expected: no TS errors

- [ ] **Step 3: Commit**

### Task 6: Deploy + verify battle with real judge

**Files:**
- None, deploy steps

- [ ] **Step 1: Deploy backend modal**

Run: `modal deploy modal_entry.py`

Expected: https://...modal.run/health ok, /formats 15 (14+1)

- [ ] **Step 2: Deploy frontend vercel prod**

Run: `vercel deploy . --prod --project prj_4ixQVsewtM1O8ROKkl2WMPCujK1H`

Expected: frontend-lipx... ready, alias agent-arena-blond

- [ ] **Step 3: Create battle via UI or TestClient with tool-using-coding-race, host:groq-llama + host:tokenrouter, check file tree grows, TEST_PASS badge, THEORY.md viewer, judge scores Kimi-K3**

Run: python script to create battle and poll

Expected: artifacts contain files JSON + chosen_skills 5 + theory

- [ ] **Step 4: Commit if any fix**

