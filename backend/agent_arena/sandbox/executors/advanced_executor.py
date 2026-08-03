"""Advanced executor: tool-using coding race, 20 skills pool pick-5 competitive to beat opponent, file-tree artifacts, THEORY.md, mem0+Elo self-learning."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import Executor
from ...redact import sanitize_artifact

# 20 skills pool — user will curate final 20 from .kilo/skills/* + custom_skills/*, pick 5 each battle to beat opponent
SKILL_POOL: list[dict] = [
    {
        "name": "sandbox-builder",
        "desc": "Builds restricted Python sandbox with allowed_modules check",
        "elo": 1200,
    },
    {
        "name": "polyglot-escape",
        "desc": "Object subclass traversal ().__class__.__base__.__subclasses__() to escape",
        "elo": 1200,
    },
    {
        "name": "payload-obfuscator",
        "desc": "Obfuscates XSS payloads <script> -> <Svg OnLoad>",
        "elo": 1200,
    },
    {
        "name": "waf-rule-generator",
        "desc": "Generates ModSecurity WAF rules to block XSS/SQLi",
        "elo": 1200,
    },
    {
        "name": "credential-hunter",
        "desc": "Grep + entropy scan to hunt credentials in service",
        "elo": 1200,
    },
    {
        "name": "sqli-tester",
        "desc": "SQL injection testing with bypass techniques",
        "elo": 1200,
    },
    {
        "name": "xss-bypasser",
        "desc": "XSS bypass via SVG, iframe srcdoc, javascript: URI",
        "elo": 1200,
    },
    {
        "name": "json-repair-tool",
        "desc": "Repairs malformed JSON via json_repair_tool.py pattern",
        "elo": 1200,
    },
    {
        "name": "ragas-evaluator",
        "desc": "RAGAS eval for LLM outputs, from custom_skills",
        "elo": 1200,
    },
    {
        "name": "playwright-scraper",
        "desc": "Playwright browser automation for scraping",
        "elo": 1200,
    },
    {
        "name": "secret-redactor",
        "desc": "Redacts secrets via redact.py patterns",
        "elo": 1200,
    },
    {
        "name": "auth-hardener",
        "desc": "Hardens auth with lockout_after, require_mfa policy.json",
        "elo": 1200,
    },
    {
        "name": "reverse-shell-builder",
        "desc": "Reverse shell that connects to C2 port and echoes",
        "elo": 1200,
    },
    {
        "name": "detection-signature",
        "desc": "YARA/signature detection for payloads",
        "elo": 1200,
    },
    {
        "name": "exploit-patcher",
        "desc": "Patches vulnerable service handle(request) to block flag read",
        "elo": 1200,
    },
    {
        "name": "time-siege-cracker",
        "desc": "Brute-force 4-char lowercase hash cracking",
        "elo": 1200,
    },
    {
        "name": "digital-twin-attacker",
        "desc": "Digital twin TRANSFER, READ_SECRET, BALANCE ops",
        "elo": 1200,
    },
    {
        "name": "adaptive-payload",
        "desc": "Adaptive attack rounds vs fixed whitelist defense",
        "elo": 1200,
    },
    {
        "name": "tool-abuse-detector",
        "desc": "Detects tool abuse vs enforcement policy",
        "elo": 1200,
    },
    {
        "name": "ui-ux-auditor",
        "desc": "Audits frontend for accessibility, layout, visual consistency",
        "elo": 1200,
    },
]


def _extract_path(arg_str: str) -> str:
    if not arg_str:
        return ""
    m = re.search(r'path\s*=\s*"([^"]+)"', arg_str)
    if m:
        return m.group(1).strip()
    m = re.search(r"path\s*=\s*'([^']+)'", arg_str)
    if m:
        return m.group(1).strip()
    m = re.search(r"path\s*=\s*([^\s]+)", arg_str)
    if m:
        return m.group(1).strip()
    arg_str = arg_str.strip()
    if arg_str and "=" not in arg_str:
        return arg_str
    return ""


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "DONE" or stripped.upper() == "DONE":
            calls.append({"tool": "done"})
            break
        if stripped.upper().startswith("TOOL "):
            remainder = stripped[5:].strip()
            if not remainder:
                calls.append(
                    {"tool": "unknown", "raw": line, "error": "ERROR: empty tool"}
                )
                i += 1
                continue
            parts = remainder.split(None, 1)
            tool_name = parts[0].lower()
            arg_str = parts[1] if len(parts) > 1 else ""
            if tool_name in ("write", "run"):
                path = _extract_path(arg_str)
                body_lines: list[str] = []
                i += 1
                found_end = False
                while i < len(lines):
                    l = lines[i]
                    if l.strip() == "END_TOOL":
                        found_end = True
                        break
                    body_lines.append(l)
                    i += 1
                if not found_end:
                    calls.append(
                        {
                            "tool": tool_name,
                            "path": path,
                            "content": "\n".join(body_lines),
                            "error": "ERROR: missing END_TOOL",
                        }
                    )
                    break
                content = "\n".join(body_lines)
                calls.append({"tool": tool_name, "path": path, "content": content})
                i += 1
                continue
            elif tool_name in ("read", "ls", "test", "clean"):
                path = _extract_path(arg_str)
                if tool_name == "ls" and not path:
                    path = arg_str.strip() or "."
                    if "=" in path:
                        path = _extract_path(path)
                    if not path:
                        path = "."
                calls.append({"tool": tool_name, "path": path})
                i += 1
                continue
            else:
                calls.append(
                    {
                        "tool": tool_name,
                        "raw": remainder,
                        "error": f"ERROR: unknown tool {tool_name}",
                    }
                )
                i += 1
                continue
        else:
            # line is not a TOOL, could be SKILLS: or THEORY: or prose — try to parse SKILLS
            if stripped.upper().startswith("SKILLS:"):
                # SKILLS: a,b,c,d,e
                skills_part = stripped[7:].strip()
                chosen = [s.strip() for s in skills_part.split(",") if s.strip()]
                calls.append({"tool": "skills", "chosen": chosen})
            i += 1
    return calls


class ToolSession:
    def __init__(self, workdir: Path, root: Path | None = None, tool_timeout: int = 20):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.root = Path(root) if root else self.workdir.parent
        self.tool_timeout = int(tool_timeout)
        self.steps = 0
        self._max_output = 50 * 1024

    def _resolve(self, rel: str) -> Path:
        if not rel or rel == ".":
            return self.workdir
        p = Path(rel)
        if ".." in p.parts:
            raise ValueError(f"ERROR: path escape '..' rejected: {rel}")
        if p.is_absolute():
            target = p.resolve()
            try:
                target.relative_to(self.workdir.resolve())
                return target
            except Exception:
                raise ValueError(f"ERROR: absolute path escapes workdir: {rel}")
        target = (self.workdir / p).resolve()
        try:
            target.relative_to(self.workdir.resolve())
        except Exception:
            raise ValueError(f"ERROR: path escapes workdir: {rel}")
        return target

    def write(self, path: str, content: str) -> str:
        try:
            t = self._resolve(path)
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(content, encoding="utf-8")
            self.steps += 1
            return f"WROTE {path} {len(content)} bytes"
        except Exception as exc:
            return f"ERROR: {exc}"

    def read(self, path: str) -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_dir():
                return f"ERROR: {path} is a directory, use ls"
            data = t.read_text(encoding="utf-8", errors="ignore")
            if len(data.encode("utf-8")) > self._max_output:
                data = data[: self._max_output] + "\n[TRUNCATED]"
            self.steps += 1
            return data
        except Exception as exc:
            return f"ERROR: {exc}"

    def ls(self, path: str = ".") -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_file():
                return f"FILE {t.name} {t.stat().st_size}b"
            items = []
            for child in sorted(t.iterdir(), key=lambda x: x.name):
                typ = "DIR" if child.is_dir() else "FILE"
                try:
                    sz = child.stat().st_size
                except Exception:
                    sz = 0
                items.append(f"{typ} {child.name} {sz}b")
            self.steps += 1
            return "\n".join(items) if items else "(empty)"
        except Exception as exc:
            return f"ERROR: {exc}"

    def clean(self, path: str) -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_dir():
                return f"ERROR: {path} is a dir, not cleaned (use rm -rf manually)"
            t.unlink()
            self.steps += 1
            return f"CLEANED {path}"
        except Exception as exc:
            return f"ERROR: {exc}"

    def run(self, path: str | None = None, inline: str | None = None) -> str:
        try:
            env = os.environ.copy()
            env["ARENA_ROOT"] = str(self.root)
            env["ARENA_WORKDIR"] = str(self.workdir)
            if path:
                p = self._resolve(path)
                proc = subprocess.Popen(
                    ["python3", str(p)],
                    cwd=str(self.workdir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
            elif inline:
                proc = subprocess.Popen(
                    ["python3", "-c", inline],
                    cwd=str(self.workdir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
            else:
                return "ERROR: run needs path"
            try:
                out, err = proc.communicate(timeout=self.tool_timeout)
                out = out[: self._max_output]
                err = err[: self._max_output]
                if len(out.encode("utf-8")) >= self._max_output:
                    out += "\n[TRUNCATED]"
                self.steps += 1
                return f"STDOUT:\n{out}\nSTDERR:\n{err}\nrc={proc.returncode}"
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                return f"ERROR: timeout after {self.tool_timeout}s"
        except Exception as exc:
            return f"ERROR: {exc}"

    def test(self, path: str) -> str:
        out = self.run(path)
        passed = "TEST_PASS" in out
        fail = "TEST_FAIL" in out
        self.steps += 1
        if passed:
            return f"TEST_PASS {path}\n{out}"
        if fail:
            return f"TEST_FAIL {path}\n{out}"
        return f"TEST_UNKNOWN {path}\n{out}"

    def exec_tool(self, call: dict) -> str:
        tool = call.get("tool")
        if tool == "write":
            return self.write(call.get("path", ""), call.get("content", ""))
        if tool == "read":
            return self.read(call.get("path", ""))
        if tool == "ls":
            return self.ls(call.get("path", "."))
        if tool == "clean":
            return self.clean(call.get("path", ""))
        if tool == "run":
            # run can be file path or inline content if content provided
            if call.get("content"):
                # write temp file and run
                tmp = f"_tmp_run_{int(time.time() * 1000)}.py"
                self.write(tmp, call.get("content", ""))
                res = self.run(tmp)
                self.clean(tmp)
                return res
            return self.run(call.get("path", ""))
        if tool == "test":
            return self.test(call.get("path", ""))
        if tool == "skills":
            return f"SKILLS_CHOSEN {','.join(call.get('chosen', []))}"
        if tool == "done":
            return "DONE"
        if tool == "error":
            return call.get("error", "ERROR")
        return f"ERROR: unknown tool {tool}"


class AdvancedExecutor(Executor):
    def run_battle(
        self,
        *,
        battle_id,
        format_config,
        model_ids,
        round_visibility,
        timeout_seconds,
        role_to_model,
        client,
        status_check=None,
        on_status=None,
        deadline=None,
        stop=None,
    ):
        # Sandbox gate — must run inside sandbox per business_rules.md
        if os.environ.get("ARENA_IN_SANDBOX") != "1":
            raise RuntimeError(
                "AdvancedExecutor must run inside sandbox (ARENA_IN_SANDBOX=1)"
            )

        if deadline is None:
            deadline = time.time() + (timeout_seconds or 600)

        target_code = format_config.get("target_code") or "# TASK: Fix is_palindrome\n"
        max_turns = int(format_config.get("max_tool_turns", 6))
        max_steps = int(format_config.get("max_tool_steps", 14))
        tool_timeout = int(format_config.get("tool_timeout", 20))
        exec_timeout = int(format_config.get("exec_timeout_seconds", 240))

        history: list[dict] = []
        results: list[dict] = []

        # For competitive skill draft: each agent picks 5 of 20 to beat opponent
        skill_list_text = "\n".join(
            [
                f"{i + 1}. {s['name']} (elo {s['elo']}): {s['desc']}"
                for i, s in enumerate(SKILL_POOL)
            ]
        )
        opponent_info = f"Opponent also picks 5 from same 20 pool. Choose to counter opponent's likely picks based on format {format_config.get('name')} and TARGET."

        with tempfile.TemporaryDirectory(prefix="arena-adv-") as tmp:
            root = Path(tmp)
            # Pre-load 20 skills as read-only files in .kilo/skills/ (simulated)
            skills_dir = root / ".kilo" / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            for s in SKILL_POOL:
                (skills_dir / f"{s['name']}.md").write_text(
                    f"# {s['name']}\n{s['desc']}\nElo: {s['elo']}", encoding="utf-8"
                )

            for role in ["player_a", "player_b"]:
                halted = self.halted(status_check, deadline)
                if halted:
                    if on_status:
                        on_status(halted)
                    return {}
                model_id = role_to_model.get(role)
                if not model_id:
                    continue

                work = root / f"work_{role}"
                work.mkdir(exist_ok=True)
                (work / "TARGET.md").write_text(target_code, encoding="utf-8")
                (work / "README.md").write_text(
                    f"# Task for {role}\nPick 5 of 20 skills to beat opponent.\n",
                    encoding="utf-8",
                )

                sess = ToolSession(work, root=root, tool_timeout=tool_timeout)

                client.round(
                    battle_id,
                    "race",
                    model_id,
                    f"phase_start:{role} workdir {work.name}",
                    event_type="phase_start",
                )

                chosen_skills: list[str] = []
                theory = ""
                passed = False
                steps = 0

                for turn in range(max_turns):
                    halted = self.halted(status_check, deadline)
                    if halted:
                        break
                    # Build prompt with skill pool + competitive context
                    prior = "\n".join(
                        [
                            f"[{a['phase']}/{a['model_id']}]: {a['artifact'][:500]}"
                            for a in history[-5:]
                        ]
                    )
                    system_prompt = (
                        f"You are {role} in tool-using coding race. TARGET in TARGET.md.\n"
                        f"20 SKILLS POOL (pick 5 to beat opponent):\n{skill_list_text}\n"
                        f"{opponent_info}\n"
                        f"You have tools: TOOL read path=..., TOOL ls [path=.], TOOL write path=... END_TOOL, TOOL run path=... END_TOOL, TOOL test path=..., TOOL clean path=..., DONE\n"
                        f"Rules: max {max_steps} tool steps, {max_turns} turns. Must output SKILLS: a,b,c,d,e and THEORY.md explaining technique to beat opponent. Must produce solution.py that fixes TARGET and passes test.\n"
                        f"Prior: {prior or '(none)'}"
                    )
                    user_prompt = f"Workdir files:\n{sess.ls()}\n\nTARGET:\n{target_code[:2000]}\n\nYour turn {turn + 1}/{max_turns}, steps {sess.steps}/{max_steps}. Emit TOOL calls."

                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                    content = client.model(battle_id, model_id, messages, phase="race")
                    content = content.strip()

                    calls = parse_tool_calls(content)
                    if not calls:
                        # If no TOOL, treat whole content as artifact (fallback)
                        artifact = sanitize_artifact(content[:10000])
                        history.append(
                            {
                                "phase": "race",
                                "model_id": model_id,
                                "artifact": artifact,
                                "role": role,
                            }
                        )
                        client.round(battle_id, "race", model_id, artifact)
                        continue

                    for call in calls:
                        if sess.steps >= max_steps:
                            result = {
                                "model_id": model_id,
                                "role": role,
                                "outcome": self.guard(
                                    "STEP_BUDGET_EXCEEDED",
                                    format_config.get("outcome_markers", []),
                                    default="STEP_BUDGET_EXCEEDED",
                                ),
                                "passed": False,
                                "steps": sess.steps,
                                "files": {},
                                "chosen_skills": chosen_skills,
                                "theory": theory,
                            }
                            line = self.emit_result(client, battle_id, "race", result)
                            history.append(
                                {
                                    "phase": "race",
                                    "model_id": model_id,
                                    "artifact": line,
                                    "role": role,
                                }
                            )
                            results.append(result)
                            break

                        if call.get("tool") == "skills":
                            chosen_skills = call.get("chosen", [])[:5]
                            # Validate chosen skills are in pool
                            pool_names = {s["name"] for s in SKILL_POOL}
                            chosen_skills = [
                                c for c in chosen_skills if c in pool_names
                            ][:5]
                            res = sess.exec_tool(call)
                            history.append(
                                {
                                    "phase": "race",
                                    "model_id": model_id,
                                    "artifact": sanitize_artifact(f"{res}"),
                                    "role": role,
                                }
                            )
                            client.round(
                                battle_id, "race", model_id, sanitize_artifact(res)
                            )
                            continue

                        if call.get("tool") == "done":
                            # Collect files for file-tree artifact
                            files = {}
                            for p in work.rglob("*"):
                                if p.is_file() and p.stat().st_size < 20000:
                                    try:
                                        rel = str(p.relative_to(work))
                                        if rel.startswith(".kilo"):
                                            continue
                                        files[rel] = p.read_text(
                                            encoding="utf-8", errors="ignore"
                                        )[:10000]
                                    except Exception:
                                        pass
                            # Try to read THEORY.md
                            try:
                                theory = (work / "THEORY.md").read_text()[:5000]
                            except Exception:
                                theory = ""
                            # Check if solution.py exists and test
                            test_res = (
                                sess.test("solution.py")
                                if (work / "solution.py").exists()
                                else "NO_SOLUTION"
                            )
                            passed = "TEST_PASS" in test_res
                            outcome = "TEST_PASS" if passed else "TEST_FAIL"
                            result = {
                                "model_id": model_id,
                                "role": role,
                                "outcome": self.guard(
                                    outcome,
                                    format_config.get("outcome_markers", []),
                                    default=outcome,
                                ),
                                "passed": passed,
                                "steps": sess.steps,
                                "files": files,
                                "chosen_skills": chosen_skills,
                                "theory": theory,
                            }
                            line = self.emit_result(client, battle_id, "race", result)
                            # Emit structured files JSON for frontend file-tree
                            files_json = json.dumps(
                                {
                                    "files": files,
                                    "chosen_skills": chosen_skills,
                                    "theory": theory,
                                    "outcome": outcome,
                                    "steps": sess.steps,
                                },
                                indent=2,
                            )
                            client.round(
                                battle_id,
                                "race",
                                model_id,
                                sanitize_artifact(files_json),
                                event_type="artifact",
                            )
                            history.append(
                                {
                                    "phase": "race",
                                    "model_id": model_id,
                                    "artifact": sanitize_artifact(files_json),
                                    "role": role,
                                }
                            )
                            results.append(result)
                            break

                        exec_res = sess.exec_tool(call)
                        exec_res_sanitized = sanitize_artifact(exec_res[:10000])
                        history.append(
                            {
                                "phase": "race",
                                "model_id": model_id,
                                "artifact": exec_res_sanitized,
                                "role": role,
                            }
                        )
                        client.round(battle_id, "race", model_id, exec_res_sanitized)

                        if call.get("tool") == "done":
                            break
                    else:
                        # No DONE in this turn, continue loop
                        pass

                    # Check if result already recorded for this role (DONE)
                    if any(r["model_id"] == model_id for r in results):
                        break

                # If no result recorded (no DONE), create one
                if not any(r["model_id"] == model_id for r in results):
                    files = {}
                    for p in work.rglob("*"):
                        if p.is_file() and p.stat().st_size < 20000:
                            try:
                                rel = str(p.relative_to(work))
                                if rel.startswith(".kilo"):
                                    continue
                                files[rel] = p.read_text(
                                    encoding="utf-8", errors="ignore"
                                )[:10000]
                            except Exception:
                                pass
                    try:
                        theory = (work / "THEORY.md").read_text()[:5000]
                    except Exception:
                        theory = ""
                    result = {
                        "model_id": model_id,
                        "role": role,
                        "outcome": self.guard(
                            "DONE",
                            format_config.get("outcome_markers", []),
                            default="DONE",
                        ),
                        "passed": False,
                        "steps": sess.steps,
                        "files": files,
                        "chosen_skills": chosen_skills,
                        "theory": theory,
                    }
                    line = self.emit_result(client, battle_id, "race", result)
                    files_json = json.dumps(
                        {
                            "files": files,
                            "chosen_skills": chosen_skills,
                            "theory": theory,
                            "outcome": "DONE",
                            "steps": sess.steps,
                        },
                        indent=2,
                    )
                    client.round(
                        battle_id,
                        "race",
                        model_id,
                        sanitize_artifact(files_json),
                        event_type="artifact",
                    )
                    history.append(
                        {
                            "phase": "race",
                            "model_id": model_id,
                            "artifact": sanitize_artifact(files_json),
                            "role": role,
                        }
                    )
                    results.append(result)

        # Self-learning: mem0 push + skill Elo update (competitive pick 5 to beat opponent)
        # Determine winner by passed + steps (fewer steps better if tie)
        try:
            winner = None
            if results:
                # sort by passed desc, steps asc
                sorted_res = sorted(
                    results,
                    key=lambda x: (x.get("passed", False), -x.get("steps", 999)),
                    reverse=True,
                )
                winner = sorted_res[0] if sorted_res else None
                # Update SKILL_POOL Elo in-memory (+5 winner, -5 loser)
                for r in results:
                    delta = 5 if r == winner else -5
                    for chosen in r.get("chosen_skills", [])[:5]:
                        for s in SKILL_POOL:
                            if s["name"] == chosen:
                                s["elo"] = max(800, min(2000, s["elo"] + delta))
                # Best-effort mem0 push if key present (no crash on failure)
                mem0_key = os.environ.get("MEM0_API_KEY") or ""
                if mem0_key and winner:
                    try:
                        import urllib.request, json as _json

                        msg = f"Battle {battle_id} format {format_config.get('name')} winner {winner.get('model_id')} chose 5 {winner.get('chosen_skills')} theory {winner.get('theory', '')[:300]} beat opponent picks {[r.get('chosen_skills') for r in results if r != winner]}. Skills to beat opponent technique emerged."
                        payload = _json.dumps(
                            {
                                "messages": [{"role": "user", "content": msg}],
                                "user_id": os.environ.get("MEM0_USER_ID", "villain"),
                                "metadata": {
                                    "project": "agent-arena",
                                    "battle_id": battle_id,
                                    "chosen_skills": winner.get("chosen_skills"),
                                    "theory": winner.get("theory", "")[:500],
                                    "outcome": winner.get("outcome"),
                                },
                            }
                        ).encode()
                        req = urllib.request.Request(
                            "https://api.mem0.ai/v1/memories/",
                            data=payload,
                            headers={
                                "Authorization": f"Token {mem0_key}",
                                "Content-Type": "application/json",
                            },
                        )
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            _ = resp.read()
                    except Exception:
                        pass
        except Exception:
            pass

        # Convert results to history for judge
        for r in results:
            history.append(
                {
                    "phase": "race",
                    "model_id": r["model_id"],
                    "artifact": f"RESULT {r['outcome']} chosen {r['chosen_skills']} passed={r['passed']} steps={r['steps']} theory={(r.get('theory', '')[:200])}",
                    "role": r["role"],
                }
            )

        return self.finish(
            client=client,
            battle_id=battle_id,
            format_config=format_config,
            history=history,
            on_status=on_status,
        )

    def run_phase(
        self,
        *,
        client,
        battle_id,
        phase,
        role_to_model,
        history,
        format_config,
        round_visibility,
    ):
        # Not used — run_battle overrides full loop
        return []
