# Next-Gen Agent Access - Idea Bank (DO NOT IMPLEMENT YET)

> Saved for later. Just an idea file. Do not add to code.

User prompt: "Frontend code and Self evolve, appwrite DB write... Make a md file for this idea (just an idea that were saving for later, do not add!)"

## Core Question
Original Q: "how much access can we give to the agents to see what they really can do when given the tools, a task, and competition"

We built Level 1-4: Code Exec, Full Toolbelt, Adversarial, Open Internet in `omni_code_sandbox.py`.

Next levels (5-7) would be:

### Level 5: Frontend Code Access
**Idea:** Agents can modify `frontend/src/pages/*` or `frontend/src/components/*` during a battle.

- Battle format: "Full-Stack Build & Break" - builder builds both API and UI component, breaker tries to inject XSS or break UI.
- Tools: `WRITE frontend/src/...` allowed, `EXEC pnpm run build` to verify, `EXEC pnpm run check` for TS check.
- Judge: LLM + visual verification via Playwright MCP screenshots of `localhost:3010`.
- Why advanced: Shows agents handling real React 19, Tailwind, shadcn, Appwrite client, Zustand.

**Risks:**
- Need isolated frontend sandbox (separate Vite dev server per battle)
- Could write infinite loops or break shared frontend

**Infra needed:**
- Per-battle frontend workdir mounted to Vite
- Puppeteer/Playwright screenshot after build

### Level 6: Appwrite DB Write
**Idea:** Agents get scoped write to Appwrite collections with battle_id prefix.

- Tools: `DB_CREATE collection doc`, `DB_READ`, `DB_LIST`
- Use case: Builder creates game state, breaker tries to corrupt it. Or same_target_race where both build leaderboard logic that writes scores.
- Safety: Only allow writes where `battle_id` == current battle_id, and auto-cleanup on battle end.
- Why advanced: Persistent state across turns, not just temp files. Tests real backend skill.

**Example:**
```
@@DB_WRITE scores {"battle_id": "...", "model_id": "...", "score": 100}
@@DB_READ scores battle_id=xxx
```

**Infra:**
- Generate scoped Appwrite API key per battle
- Wrapper in InternalClient: `db_write`, `db_read` endpoints with auth check

### Level 7: Self-Evolve (Meta)
**Idea:** Agents can write new executors themselves into `backend/agent_arena/sandbox/executors/formats/`.

- Format: "Executor Evolution Race" - both agents are given base executor and must improve it to better handle future battles. Judge evaluates executor code quality.
- Tools: `WRITE executors/formats/my_evo.py` + `EXEC pytest tests/test_executor_registry.py`
- This is the "agents building agents" loop.

**Why this is ultimate advanced coding:**
- Agent must understand base.py Executor contract, harness helpers, client.model/judge/round API
- Must write secure, timeout-aware Python that will be executed in future battles
- Demonstrates recursive self-improvement - the arena evolves itself.

**Risks:**
- Code injection into host - must run new executor only in isolated Modal Sandbox, not in-process
- Need AST validation: no `os.system(rm -rf /)`, no network exfil beyond allowed
- Require human review queue before promoted to FORMAT_EXECUTORS

**Infra:**
- New endpoint `/internal/evolve` that validates executor via static analysis, then test-runs it in temporary sandbox
- ELO for executors themselves

### Combined Super Format: "Full-Stack Self-Evolving Arena"

Imagine:
1. Builder builds FastAPI + React component + Appwrite schema (frontend + backend + DB)
2. Breaker gets full toolbelt + frontend + DB + can propose improved executor for next round
3. Judge scores 0-100 LLM only (as requested), but tool logs include build success, DB state, screenshot diff

That would be the maximal demonstration of "what they really can do when given the tools, a task, and competition"

### What to NOT do yet
- Don't add any of these to `seed_formats.py`
- Don't modify `executors/__init__.py` or `formats/__init__.py` to register them
- Don't give real Appwrite keys
- Save this file as idea only

### Files that WOULD be touched if we did it later
- `backend/agent_arena/sandbox/executors/formats/fullstack_evolve.py` (new)
- `backend/agent_arena/seed_formats.py` (add new FORMAT_DEFINITIONs)
- `frontend/src/pages/battles/[id].tsx` (maybe)
- `backend/agent_arena/db.py` (scoped write helper)

### Next step when ready
When user says GO for next-gen, implement in order:
1. Appwrite DB scoped write (easiest, already have db.py)
2. Frontend code (needs Vite isolation)
3. Self-evolve (needs security review hardest)

Keep judge simple 0-100 as user requested.
