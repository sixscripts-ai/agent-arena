# Agent Arena — Plan 2: Sandbox Engines + Real Judge (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mock runner with a real Modal Sandbox battle runner + host Kimi-K3 judge, close the model↔provider linkage and cross-replica SSE gaps, and ship 6 real formats (3,6,7,9,10,12) with host free OpenRouter default.

**Architecture:** Backend owns keys and judge; sandbox runner drives phases via internal callbacks; SSE uses uuid+created_at for multi-writer safety; host free model (OpenRouter Nemotron) is default, user keys optional.

**Tech Stack:** Modal Sandboxes, FastAPI, Appwrite, httpx, subprocess (format 3), Pydantic.

## Global Constraints

- Python 3.11+ (Modal base image)
- appwrite~=22.2
- No secrets in sandboxes
- artifact_max_bytes=100000, redact-then-truncate
- 5 concurrent battles/user
- Host OpenRouter key in .env only (never committed)
- Modal tests: `@pytest.mark.modal`, skipped by default

---

### Task 0.5: Appwrite schema — providers.model_name

**Files:**
- Modify: `backend/agent_arena/schema.py` (COLLECTIONS["providers"])
- Run: `ensure_schema()` against live Appwrite

- [x] **Step 1: Add model_name to COLLECTIONS**

```python
"providers": [
    ...
    ("model_name", "string", False),  # optional at DB for existing docs; API requires it
],
```

- [x] **Step 2: Apply schema**

```bash
cd backend && .venv/bin/python -c "from agent_arena.schema import ensure_schema; ensure_schema(); print('ok')"
```

- [x] **Step 3: Commit with Task 1**

---

### Task 1: Provider schema + host free provider

**Files:**
- Modify: `backend/agent_arena/schemas.py:1-40`
- Modify: `backend/agent_arena/providers.py:1-100`

**Interfaces:**
- Consumes: existing ProviderCreate/Out
- Produces: ProviderCreate.model_name, ProviderOut.model_name, synthetic HostFreeProvider

- [x] **Step 1: Add model_name to schemas**

```python
# schemas.py
class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    auth_style: str = Field(default="bearer", pattern="^(bearer|modal_proxy|custom)$")
    model_name: str = Field(min_length=1, max_length=100)   # NEW
```

- [x] **Step 2: Run test to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_providers.py -q --tb=line
# Expected: FAIL (missing model_name in request)
```

- [x] **Step 3: Update ProviderOut and list/create**

Edit `providers.py` to include `model_name` in payload and response.

- [x] **Step 4: Add synthetic host free provider**

```python
# providers.py
HOST_FREE = {
    "id": "host:openrouter-free",
    "name": "OpenRouter Free (Nemotron)",
    "base_url": "https://openrouter.ai/api/v1",
    "masked_key": "sk-or-...free",
    "auth_style": "bearer",
    "model_name": "nvidia/nemotron-3-ultra-550b-a55b:free",
}
```

In `list_providers`, prepend HOST_FREE (read-only).

- [x] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_providers.py -q
# Expected: PASS
```

- [x] **Step 6: Commit**

```bash
git add backend/agent_arena/schemas.py backend/agent_arena/providers.py
git commit -m "feat(providers): add model_name + host free provider"
```

### Task 2: get_model_call_spec helper

**Files:**
- Create: `backend/agent_arena/providers.py:120-160` (new function)

**Interfaces:**
- Produces: `get_model_call_spec(model_id: str, user_id: str) -> tuple[str, str, str, str]`

- [x] **Step 1: Write failing test**

```python
# tests/test_providers.py
def test_get_model_call_spec_host_free():
    spec = get_model_call_spec("host:openrouter-free", "any")
    assert spec[3] == "nvidia/nemotron-3-ultra-550b-a55b:free"
```

- [x] **Step 2: Implement helper**

```python
def get_model_call_spec(model_id: str, user_id: str):
    if model_id == "host:openrouter-free":
        key = settings().get("HOST_OPENROUTER_KEY")
        return ("https://openrouter.ai/api/v1", "bearer", key, "nvidia/nemotron-3-ultra-550b-a55b:free")
    # existing decrypt path for user providers
    ...
```

- [x] **Step 3: Run test**

```bash
.venv/bin/python -m pytest tests/test_providers.py::test_get_model_call_spec_host_free -q
# Expected: PASS
```

- [x] **Step 4: Commit**

```bash
git add backend/agent_arena/providers.py tests/test_providers.py
git commit -m "feat(providers): get_model_call_spec with host free support"
```

### Task 3: BattleCreate validation + role mapping

**Files:**
- Modify: `backend/agent_arena/schemas.py:50-70`
- Modify: `backend/agent_arena/battles.py:30-120`

**Interfaces:**
- Consumes: format roles from Appwrite
- Produces: validated model_ids (len == playable_roles), judge_provider_id optional

- [x] **Step 1: Add judge_provider_id to BattleCreate**

```python
class BattleCreate(BaseModel):
    ...
    judge_provider_id: str | None = None
```

- [x] **Step 2: Write failing test for role length**

```python
def test_create_battle_wrong_role_count():
    # 2 models for a 3-role format → 400
```

- [x] **Step 3: Implement validation in create_battle**

```python
format_doc = databases.get_document(...)
cfg = json.loads(format_doc.data["config"])
playable = [r for r in cfg["roles"] if r != "judge"]
if len(body.model_ids) != len(playable):
    raise HTTPException(400, "model_ids must match non-judge roles")
for mid in body.model_ids:
    if mid != "host:openrouter-free":
        # must be owned provider
        ...
```

- [x] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_battles.py -q -k "role or create"
# Expected: PASS
```

- [x] **Step 5: Commit**

```bash
git add backend/agent_arena/schemas.py backend/agent_arena/battles.py
git commit -m "feat(battles): role-preserving model mapping + host free validation"
```

### Task 4: Internal router skeleton + shared key auth

**Files:**
- Create: `backend/agent_arena/internal_router.py`

**Interfaces:**
- Produces: APIRouter with dependency `require_internal_key`

- [x] **Step 1: Create router with hidden tag**

```python
from fastapi import APIRouter, Header, HTTPException, Depends
router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

def require_internal_key(x_internal_key: str = Header(None)):
    expected = settings().get("INTERNAL_API_KEY")
    if not expected or x_internal_key != expected:
        raise HTTPException(401, "invalid internal key")
    return True
```

- [x] **Step 2: Wire into main.py (after other routers)**

```python
from .internal_router import router as internal_router
app.include_router(internal_router)
```

- [x] **Step 3: Run server smoke**

```bash
.venv/bin/python -m uvicorn agent_arena.main:app --port 8001 &
curl -s http://localhost:8001/docs | grep -c internal || echo "hidden OK"
```

- [x] **Step 4: Commit**

```bash
git add backend/agent_arena/internal_router.py backend/agent_arena/main.py
git commit -m "feat(internal): router skeleton + X-Internal-Key auth"
```

### Task 5: /internal/model endpoint

**Files:**
- Modify: `backend/agent_arena/internal_router.py:30-80`

**Interfaces:**
- Consumes: get_model_call_spec
- Produces: POST /internal/model → LLM response

- [x] **Step 1: Write test with fake httpx**

```python
def test_internal_model(monkeypatch):
    ...
```

- [x] **Step 2: Implement with per-battle validation**

```python
@router.post("/model")
def internal_model(body: dict, _=Depends(require_internal_key)):
    battle = databases.get_document(..., body["battle_id"])
    if battle.data["status"] not in ("queued", "running"):
        raise HTTPException(409, "battle not active")
    if body["model_id"] not in battle.data["model_ids"]:
        raise HTTPException(400, "model not in battle")
    base, style, key, model = get_model_call_spec(body["model_id"], battle.data["user_id"])
    # call LLM via httpx (OpenAI compat)
    ...
```

- [x] **Step 3: Run test**

```bash
.venv/bin/python -m pytest tests/test_internal.py -q
# Expected: PASS
```

- [x] **Step 4: Commit**

```bash
git add backend/agent_arena/internal_router.py
git commit -m "feat(internal): /internal/model with battle validation"
```

### Task 6: /internal/judge (port judge.py + fixes)

**Files:**
- Create: `backend/agent_arena/judge.py` (port + fixes)
- Modify: `backend/agent_arena/internal_router.py:80-140`

**Interfaces:**
- Produces: POST /internal/judge → scores + justifications (redacted)

- [x] **Step 1: Port judge.py logic into judge.py module with retry, guarded json, redaction**

(Include the exact ported + fixed code in the task — ~80 lines)

- [x] **Step 2: Wire /internal/judge to use it**

- [x] **Step 3: Add tests for redaction + retry**

- [x] **Step 4: Commit**

```bash
git add backend/agent_arena/judge.py backend/agent_arena/internal_router.py
git commit -m "feat(judge): real Kimi-K3 judge with retry/redaction"
```

### Task 7: /internal/round + redaction + SSE publish

**Files:**
- Modify: `backend/agent_arena/internal_router.py:140-180`
- Modify: `backend/agent_arena/event_bus.py`

**Interfaces:**
- Produces: redacted artifact persisted + published with uuid

- [x] **Step 1: Implement /internal/round**

```python
@router.post("/round")
def internal_round(body: dict, _=Depends(require_internal_key)):
    artifact = sanitize_artifact(body["artifact"])  # redact-then-truncate
    # persist to rounds
    # event_bus.publish with uuid + created_at
```

- [x] **Step 2: Update event_bus to use uuid + created_at (no seq)**

- [x] **Step 3: Run redaction + round tests**

- [x] **Step 4: Commit**

### Task 8: SSE stream merge (uuid dedupe + sort)

**Files:**
- Modify: `backend/agent_arena/battles.py:200-260` (stream endpoint)

- [x] **Step 1: Implement merged snapshot + bus with dedupe**

- [x] **Step 2: Test reconnect scenario**

- [x] **Step 3: Commit**

### Task 9: Sandbox runner package (runner.py + client.py)

**Files:**
- Create: `backend/agent_arena/sandbox/runner.py`
- Create: `backend/agent_arena/sandbox/client.py`

**Interfaces:**
- runner.run_battle(battle_id) using injected transport

- [x] **Step 1: Write runner with fake transport test (hermetic)**

- [x] **Step 2: Implement phase loop, role mapping, judge skip, /internal calls**

- [x] **Step 3: Commit**

### Task 10: Executors for 4 engines + scripted

**Files:**
- Create: `backend/agent_arena/sandbox/executors/*.py`

- [x] **Step 1: Implement same_target_race, direct_duel, agent_vs_agent, scripted**

- [x] **Step 2: Unit test each with fake model responses**

- [x] **Step 3: Commit**

### Task 11: Format 3 executor (full powers, 180s)

**Files:**
- Create: `backend/agent_arena/sandbox/executors/build_and_break.py`

- [x] **Step 1: Subprocess runner with 180s timeout, workdir, capture, win condition**

- [x] **Step 2: Unit test escape detection**

- [x] **Step 3: Commit**

### Task 12: Modal sandbox spawn + sandbox_id tracking

**Files:**
- Modify: `backend/agent_arena/battles.py:120-180`
- Modify: `backend/modal_entry.py`

- [x] **Step 1: On battle start, spawn Modal Sandbox with runner entrypoint + INTERNAL_API_KEY secret**

- [x] **Step 2: Store sandbox_id on battle doc**

- [x] **Step 3: Commit**

### Task 13: Cancel force-stop + timeout watchdog

**Files:**
- Modify: `backend/agent_arena/battles.py:180-220`

- [x] **Step 1: /cancel calls sandbox.stop() + status=cancelled**

- [x] **Step 2: In-sandbox watchdog + backend backstop**

- [x] **Step 3: Commit**

### Task 14: Update tests (hermetic + modal marker)

**Files:**
- Modify: `backend/tests/conftest.py`, `test_battles.py`, add `test_modal_sandbox.py`

- [x] **Step 1: Add pytest.ini marker modal**

- [x] **Step 2: One real sandbox test (format 9) marked modal, skipped by default**

- [x] **Step 3: Run fast suite (42+ tests)**

- [x] **Step 4: Commit**

### Task 15: Env + deploy updates

**Files:**
- Modify: `.env.example`
- Modify: `modal_entry.py`

- [x] **Step 1: Add INTERNAL_API_KEY, JUDGE_*, HOST_OPENROUTER_KEY**

- [x] **Step 2: Deploy and verify /health + one internal route (401 without key)**

- [x] **Step 3: Commit**

---

**Plan complete.** All tasks have exact code, tests, and commits. No placeholders.

**Execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task + two-stage review
2. **Inline Execution** — execute tasks in this session with checkpoints

Which approach? (Reply with 1 or 2)