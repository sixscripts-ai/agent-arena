# Agent Arena — Tool/Skill Abilities Framework (Handoff Prompt)

Copy everything below the line into your agent. It is a complete, self-contained
brief: project context, purpose, code-sophistication bar, the exact spec to build,
files you may and may NOT touch, and how to verify the work.

---

# BRIEF: Plug-and-play Tool/Skill Abilities for Agent Arena

You are building a new subsystem for an existing, production-grade product called
**Agent Arena**. Read this entire brief before writing any code. When in doubt,
match the existing codebase's style and conventions — inspect sibling files first.

## 1. What Agent Arena is

Agent Arena is a live AI model battle arena. Two (or more) AI models fight each
other in structured security/coding formats. Think "model vs model" competitions
with real code execution, a host judge that scores each side 0–100, and per-format
Elo rankings.

- **Frontend:** Vite + React + Tailwind (Vercel). Streams battles live via SSE.
- **Backend:** FastAPI running on **Modal** (serverless). Persistence via
  **Appwrite** (NoSQL). Deployment entry: `backend/modal_entry.py`.
- **Users** add their own LLM providers (BYOK) or use host-provided free models
  (OpenRouter free tier, DeepSeek, etc.). All LLM calls go through one
  OpenAI-compatible chat-completions interface.

### The battle lifecycle (how the backend works today)

1. A user creates a battle: picks a **format**, assigns **models** to roles
   (e.g. `builder` / `breaker`), picks timeout + visibility.
2. The battle runs inside a **sandbox** (a Modal Sandbox or an in-process runner).
   `backend/agent_arena/sandbox/runner.py::run_battle_loop` walks the format's
   phase list (`build → break → judge`), and for each phase calls an **executor**.
3. Each **executor** (`backend/agent_arena/sandbox/executors/`) calls the model
   via `client.model(...)` (which round-trips to the backend's `/internal/model`
   endpoint, which calls the real LLM provider), collects the model's text output
   as an **artifact**, sometimes executes it, and streams artifacts to the frontend
   via `client.round(...)`.
4. After all phases, the host judge scores each model and Elo updates.

Key plumbing:
- `backend/agent_arena/sandbox/client.py` — `InternalClient` with
  `.model(battle_id, model_id, messages, phase) -> str`,
  `.round(battle_id, phase, model_id, text, event_type="artifact")`,
  `.judge(...)`. Also a `FakeTransport` used in hermetic tests.
- `backend/agent_arena/sandbox/runner.py` — the battle loop.
- `backend/agent_arena/sandbox/executors/` — one executor per engine family
  (`build_and_break`, `script_vs_defense`, `same_target_race`, `direct_duel`,
  `agent_vs_agent`, `high_complexity`).
- `backend/agent_arena/seed_formats.py` — seeds 25 battle formats into Appwrite;
  each format's `config` carries `roles`, `phases`, `judge_rubric`,
  `scoring_weights`, and an `extra` dict (a plan is adding curated per-format
  targets there).

### Concurrency note (IMPORTANT — read before touching anything)

Another engineer is mid-flight on a separate plan (the "all-25 bespoke format
executors" plan) that rewrites parts of the executor layer and `seed_formats.py`.
**Your work must be a standalone addition that does not touch the files being
rewritten there** (see the DO-NOT-TOUCH list in §6). Build your subsystem so it is
self-contained and can be wired in later with a few lines. Do not attempt to
"integrate" it into battle flow or modify seed data — deliver the framework, its
tools, its loop, its skills, and its tests, fully working in isolation.

## 2. What you are building — the purpose

Right now, models in a battle are **one-shot text generators**: the executor sends
a prompt, gets text, done. Your job is to give arena models **abilities** — a
plug-and-play framework so that in a battle, a model can act as an **agent**: it
can **call tools** (read files, write files, run code, fetch URLs) and **invoke
skills** (load a SKILL.md-style procedure and apply it), iterating until its
objective is met.

The product vision (from the product owner):
- **Plug-and-play:** adding one new ability must be one module + one registration
  line. No rewriting the codebase. This is a hard requirement.
- **Skills as abilities:** SKILL.md-style bundles (like the user's own skill
  libraries) become abilities a model can load and follow.
- **Text protocol:** models call tools by writing a plain-text action line
  (`TOOL:name key="value"`), NOT native function-calling APIs. Reason: host
  free-tier models often lack function-calling support; the text protocol works on
  *every* OpenAI-compatible provider. This is a hard requirement.
- **Toolbelt for v1:** code toolkit (`read_file`, `write_file`, `list_dir`,
  `grep`, `run_python`) + web toolkit (`fetch`) + skill loader
  (`list_skills`, `use_skill`). Explicitly OUT of scope: a raw shell tool.

## 3. The sophistication bar

This is production-grade backend Python on an existing codebase. The bar:

- **Match existing conventions.** Inspect sibling files. The codebase uses:
  `from __future__ import annotations`, full type hints, small focused modules,
  `class Tool:` style OO with a registry, `@register`-style decorators, exceptions
  with clear messages, no debug prints, no placeholder/TODO stubs.
- **Do not add comments unless they explain a non-obvious decision.** The project
  convention is no decorative comments.
- **Zero new third-party dependencies.** The backend already depends on `fastapi`,
  `uvicorn`, `appwrite`, `cryptography`, `python-dotenv`, `sse-starlette`,
  `pydantic`, `httpx`. Use stdlib + `httpx` only. If you believe you need a new
  dependency, do not add it — note it in your summary and stop.
- **Hermetic tests.** All tests must run without network, without Modal, without
  Appwrite. Reuse the `FakeTransport` pattern from
  `backend/agent_arena/sandbox/client.py`. For `fetch`, monkeypatch or point at a
  local fixture server — never hit real URLs in tests.
- **Security-minded.** Tool output must be size-capped. Paths must be confined to
  the battle workdir (no path traversal). `run_python` must have a timeout and a
  capture budget. `fetch` needs a timeout + response-size cap + sane defaults.
  Skills are data (markdown), never executed code.
- **Error handling:** tools return a string (success or error) — they must NEVER
  raise out of the loop. The loop catches, formats, and feeds failures back to the
  model so it can recover. `TOOL:name` calls with unknown names or malformed args
  produce a helpful error string, not a crash.
- **Deterministic, tested, green:** run the test suite before finishing.

## 4. The spec — exactly what to build

Create a new package **`backend/agent_arena/sandbox/tools/`** (create the
directory). Contents:

### 4.1 `tools/base.py`
```python
from __future__ import annotations
from typing import Any

class Tool:
    name: str
    description: str                      # shown to models in the system prompt
    arg_schema: dict[str, str]            # arg name -> one-line help (shown to models)
    def run(self, ctx: Any, args: dict[str, str]) -> str: ...
```
- `run` returns a string result (success or error). Never raises.
- A base helper that validates args against `arg_schema` (unknown keys rejected,
  missing required keys reported) so each tool only implements happy-path logic.

### 4.2 `tools/registry.py`
- `_TOOLS: dict[str, type[Tool]]`.
- `@register(name)` class decorator (register by the class's `name` if no arg).
- `get_tool(name) -> type[Tool] | None`.
- `install_tools(names: list[str]) -> list[Tool]` — instantiate tools for a
  battle; raises `ValueError` listing any unknown names (so format authors catch
  typos at config time).
- `available() -> list[Tool]` — list every registered tool (used by `list_skills`
  analog and tests).

### 4.3 `tools/context.py`
`ToolContext` dataclass holding what a tool needs to act:
- `workdir: Path` — the battle working directory (tools confine all file ops here).
- `emit(phase: str, model_id: str, event_type: str, payload: str)` — callback the
  tools call to stream activity. Default no-op; the wiring layer later maps it to
  `client.round(...)`.
- `env: dict[str, str]` — environment for subprocesses (default empty).
- `http: httpx.Client` — shared client with sane timeouts.
- `skills_dir: Path` — root of the skills library.
- `max_output_bytes: int` (default 60_000) — all tool output is capped to this.

### 4.4 `tools/code.py` — the code toolkit (5 tools)
All file paths are **relative to `workdir`** and must be rejected if they escape
it (resolve, then check `is_relative_to(workdir)`). Include a `_safe_path(workdir, rel)` helper.
- `read_file` — args `{path}`; returns content (capped); helpful error if missing
  or binary/large.
- `write_file` — args `{path, content}`; writes inside workdir, creates parent
  dirs; returns a short confirmation (not the content).
- `list_dir` — args `{path?}` (default workdir root); returns an indented listing
  (name, dir marker, size in KB); recursive depth 1 only.
- `grep` — args `{pattern, path?}`; returns matching lines with line numbers
  (capped); stdlib `re`; invalid regex returns a helpful error.
- `run_python` — args `{path? or code?}`; accepts either a file path in workdir or
  inline `code`; executes `python3` (subprocess) in the workdir with `cwd=workdir`,
  `timeout=30`, captures stdout+stderr separately, caps each to
  `max_output_bytes`; returns combined output + exit code. Use
  `sys.executable` for the interpreter if it is `python3`/`python`, else
  `python3`; do NOT run as root; no network restriction (the sandbox already
  allows egress).

### 4.5 `tools/web.py` — the web toolkit (1 tool)
- `fetch` — args `{url}`; GET with timeout 15s, follow redirects, cap response
  body at `max_output_bytes`, return `status code` + first N chars (truncate with
  an explicit `… [truncated]` marker). Only `http`/`https` schemes allowed;
  anything else is a helpful error. Never raise out of `run` — return the error
  as a string.

### 4.6 `tools/skills.py` — the skill loader (2 tools)
A **skill** is a directory `<skills_dir>/<skill-name>/SKILL.md` whose file has YAML
frontmatter (`---\nname: …\ndescription: …\n---`) followed by markdown instructions.
This is the same shape as the user's own skill libraries — that is the point.
- `list_skills` — args `{}`; returns a numbered list of every skill name +
  description found under `skills_dir` (parse frontmatter; skip dirs without a
  valid SKILL.md; cap the listing).
- `use_skill` — args `{name}`; loads `<skills_dir>/<name>/SKILL.md`, strips the
  frontmatter, and returns the full markdown body (capped at, say, 20k chars with
  a truncation marker). The model then applies those instructions to its task.
  Unknown skill → helpful error listing available names.
- Path safety applies to the skill name too (reject `../`).

### 4.7 `tools/loop.py` — `ToolLoop`, the agent loop (the heart of the feature)
Implements the **text protocol** and the think → call → observe → act cycle.

**Protocol (hard requirement):** the model's reply is scanned line-by-line. A line
matching `TOOL:<name> <arg>=<value>…` (optionally with quoted values) is a tool
call. A line `DONE <summary>` ends the loop. Anything else is treated as normal
reasoning/thinking text. Grammar details:
- `TOOL:` at line start (allow leading whitespace).
- Args parsed as `key="quoted value"` or `key=unquoted_token`.
- One tool call per line; a reply may contain multiple `TOOL:` lines, executed in
  order.
- If a reply contains no `TOOL:` and no `DONE`, the loop continues (the model is
  "thinking") — but count it against the iteration cap so it can't spin forever.

**Class shape:**
```python
class ToolLoop:
    def __init__(self, *, ctx, client, battle_id, phase, model_id, tools,
                 objective: str, max_iters: int = 12, deadline: float | None = None): ...
    def run(self) -> list[dict]: ...
```
- `client` is an `InternalClient` (or any object with `.model(battle_id, model_id, messages, phase) -> str`).
- `tools` is the installed list of `Tool` instances.
- `run()` returns a list of **history artifacts** (the exact shape the executor
  layer expects: `[{"phase":…, "model_id":…, "artifact":…}]`), where each artifact
  is a readable transcript entry (thinking text, tool calls, tool results).

**Loop mechanics:**
1. Build the system prompt: role/objective, the battle format name, the **tool
   catalog** (name — description — args), the protocol rules (`TOOL:` / `DONE`),
   and "you are a real agent; use tools; you have at most N iterations".
2. Loop: call `client.model(...)` with the accumulated message list (system +
   prior turns). Append the reply as an assistant turn.
3. Parse the reply. Execute each `TOOL:` line via the registry inside the workdir
   context; for each call emit `ctx.emit(phase, model_id, "tool_call", …)` and
   append a `tool`-role message containing the result (this feeds observations
   back to the model).
4. On `DONE <summary>`, append a final summary message and stop.
5. Stop on: `DONE`, iteration cap reached, or `time.time() > deadline`. On cap
   reached, append an explicit "max iterations reached" note to the transcript.
6. Every tool call, result, and DONE summary must appear in the returned history
   artifacts so the judge and frontend can see the full ability usage.

**Safety in the loop:** each `TOOL:` execution is wrapped so a failing tool returns
its error string as the observation (never propagates). Malformed `TOOL:` lines
produce a `tool`-role observation explaining the parse error so the model can fix
its syntax.

### 4.8 `tools/skills/` — bundled skills (create 5 curated SKILL.md abilities)
Each is a directory with a `SKILL.md` following the frontmatter shape above.
Pick abilities that make sense for arena agents and demonstrate the loader. Good
candidates: `analyze` (multi-perspective analysis), `code-review` (review code for
bugs/risk), `debugging` (systematic bug-fix loop), `security-review` (look for
common vulns), `recon` (methodical information-gathering with fetch). Write them
to be genuinely useful and in the style of real skill libraries (frontmatter
`name` + `description`; body with Description / When to use / Instructions). Keep
each under ~60 lines. These ship with the package (so they're inside the Modal
image automatically — the image already does `add_local_python_source("agent_arena")`).

### 4.9 `tools/__init__.py`
Re-export the public surface: `Tool`, `ToolContext`, `register`, `get_tool`,
`install_tools`, `available`, `ToolLoop`. Import the tool modules so registration
happens on import. Default `SKILLS_DIR` resolution: env var `ARENA_SKILLS_DIR` if
set, else `<package>/tools/skills`.

## 5. Tests (in `backend/tests/`)

Create new test files (do not modify existing ones). Hermetic, no network, no
Modal, no Appwrite. Use `backend/.venv/bin/python -m pytest`.

- `test_tools_registry.py` — register/get/install/unknown-name errors/`available`.
- `test_tools_code.py` — each code tool against a `TemporaryDirectory` workdir:
  happy path + at least one edge each (missing file, escape attempt `../`, invalid
  regex, run_python timeout, run_python inline code, output caps).
- `test_tools_web.py` — `fetch` with a monkeypatched transport or a tiny local
  fixture server; assert scheme rejection, truncation, timeout behavior.
- `test_tools_skills.py` — `list_skills` on a fixture skills dir; `use_skill`
  returns body, strips frontmatter; unknown skill error; `../` name rejected;
  bundled `skills/` dir present and each SKILL.md parses.
- `test_tools_loop.py` — the core. Use a `FakeTransport` (from
  `backend/agent_arena/sandbox/client.py`) as the transport for `InternalClient`,
  and drive `model_replies` with a scripted sequence:
  1. First reply calls `TOOL:write_file path="x.txt" content="hello"`, second
     `DONE done writing` → assert `run()` returned artifacts containing the tool
     call, the write happened in a temp workdir, and the loop called the model
     exactly 3 times (system + 2 model turns → actually assert the message count
     evolution, not the absolute number).
  2. A sequence that never emits `DONE` → assert it stops at `max_iters`.
  3. An unknown `TOOL:name` → assert the observation fed back contains the error,
     loop continues.
  4. Malformed line → assert parse-error observation, loop continues.
  5. `deadline` respected (set a tiny deadline).
  6. `run()` artifact shape matches `[{"phase","model_id","artifact"}]`.
- Run the FULL existing suite afterwards to prove you broke nothing:
  `cd backend && .venv/bin/python -m pytest -q` (some existing tests are marked
  `modal`/`requires_appwrite` and skip locally — that is expected; there must be
  **no failures**, only skips).

## 6. Files you MAY and may NOT touch

**You MAY create/edit:**
- `backend/agent_arena/sandbox/tools/` (everything in it — the new package)
- `backend/tests/test_tools_*.py` (your new tests)

**You MUST NOT touch (another engineer is actively rewriting these):**
- `backend/agent_arena/sandbox/executors/` (any file in it)
- `backend/agent_arena/sandbox/runner.py`
- `backend/agent_arena/sandbox/client.py`
- `backend/agent_arena/sandbox_launcher.py`
- `backend/agent_arena/internal_router.py`
- `backend/agent_arena/seed_formats.py`
- `backend/pyproject.toml` and any dependency/lockfile files
- anything under `frontend/`
- any existing file in `backend/tests/`

If you find you *need* to modify a DO-NOT-TOUCH file to make your code correct,
do NOT modify it — instead make your subsystem self-contained (e.g. define your
own minimal transport/interface if needed) and note the needed wiring in your
summary.

## 7. Definition of done

1. `backend/agent_arena/sandbox/tools/` package exists with all modules in §4.
2. 5 bundled skills under `tools/skills/` (each with valid frontmatter + body).
3. All new tests pass: `cd backend && .venv/bin/python -m pytest backend/tests/test_tools_*.py -q`.
4. The FULL suite passes (only expected skips, zero failures):
   `cd backend && .venv/bin/python -m pytest -q`.
5. No DO-NOT-TOUCH file modified. Confirm with `git status --short`.
6. Zero new dependencies.
7. A concise summary at the end: what you built, the exact plug-and-play recipe
   (the two steps to add a new tool), and what wiring (2–3 lines, in which files)
   remains for the executor layer to actually activate tools in battles — do NOT
   do that wiring yourself.

## 8. Deliverable summary format

End with a short markdown block:
- Files created/changed
- The "add a new tool" recipe (concrete example)
- Remaining wiring (file + line-level suggestions, NOT performed)
- Test results (the exact commands + pass counts)
