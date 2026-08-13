"""Format-driven universal battle loop for AdvancedExecutor."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

from .advanced_executor import (
    RACE_MAX_TOKENS,
    SKILL_POOL,
    ToolSession,
    parse_tool_calls,
    select_skills,
)
from .preview import StaticPreviewServer, port_for_index, preview_enabled
from .skill_pool import load_skill_pool, mount_skills
from ...redact import sanitize_artifact


def _playable(cfg: dict) -> list[str]:
    return [r for r in (cfg.get("roles") or []) if r != "judge"]


def _mission(cfg: dict, role: str) -> str:
    missions = cfg.get("role_missions") or {}
    if role in missions:
        return str(missions[role])
    desc = str(cfg.get("description") or cfg.get("name") or "complete the objective")
    return f"You are {role}. {desc}"


def _collect_files(work: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for p in work.rglob("*"):
        if not p.is_file() or p.stat().st_size >= 20000:
            continue
        try:
            rel = str(p.relative_to(work))
        except Exception:
            continue
        if rel.startswith(".agents/skills/") and rel.endswith("SKILL.md"):
            files[rel] = "(mounted skill)"
            continue
        if rel.startswith(".kilo") or "/__pycache__/" in rel or rel.endswith(".pyc"):
            continue
        try:
            files[rel] = p.read_text(encoding="utf-8", errors="ignore")[:10000]
        except Exception:
            pass
    return files


def _copy_opponent(work: Path, workspaces: dict[str, Path], role: str) -> None:
    dest = work / "OPPONENT"
    dest.mkdir(exist_ok=True)
    for other, other_work in workspaces.items():
        if other == role or not other_work.exists():
            continue
        slot = dest / other
        slot.mkdir(exist_ok=True)
        for p in other_work.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(other_work)
            parts = rel.parts
            if parts and parts[0] in {".agents", ".kilo", "__pycache__", "OPPONENT"}:
                continue
            target = slot / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(p, target)
            except Exception:
                pass


def _want_preview(cfg: dict) -> bool:
    env = cfg.get("environment") or {}
    return bool(preview_enabled() and env.get("preview"))


def run_universal_battle(
    executor,
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
    if deadline is None:
        deadline = time.time() + (timeout_seconds or 600)

    target_code = format_config.get("target_code") or "# TASK: inspect TARGET.md and complete your mission\n"
    test_code = format_config.get("test_code")
    from .advanced_executor import DEFAULT_TEST_CODE

    if not test_code:
        test_code = DEFAULT_TEST_CODE
    max_turns = int(format_config.get("max_tool_turns", 6))
    max_steps = int(format_config.get("max_tool_steps", 14))
    raw_timeout = format_config.get("tool_timeout")
    tool_timeout = int(raw_timeout) if raw_timeout else None
    pick_n = int(format_config.get("pick_per_battle", 3))
    race_tokens = int(format_config.get("race_max_tokens") or RACE_MAX_TOKENS)
    pool = select_skills(format_config) or load_skill_pool() or SKILL_POOL
    format_name = str(format_config.get("name") or "battle")
    seq = {"n": 0}

    def emit(phase, model_id, artifact, event_type="artifact"):
        seq["n"] += 1
        client.round(
            battle_id,
            phase,
            model_id,
            artifact,
            event_type=event_type,
            sequence=seq["n"],
        )

    def emit_action(phase, model_id, action, target="", state="", duration_ms=0, result=""):
        seq["n"] += 1
        client.round(
            battle_id,
            phase,
            model_id,
            json.dumps(
                {
                    "action": action,
                    "target": target,
                    "state": state,
                    "duration_ms": int(duration_ms),
                    "result": (result or "")[:4000],
                }
            ),
            event_type="action_log",
            sequence=seq["n"],
        )

    playable = _playable(format_config) or ["player_a", "player_b"]
    phases = [
        p
        for p in (format_config.get("phases") or [])
        if any(r != "judge" for r in (p.get("participants") or []))
    ]
    if not phases:
        phases = [{"name": "race", "participants": playable, "inputs": []}]

    skill_list_text = "\n".join(
        f"{i + 1}. {s['name']} (elo {s['elo']}): {s['desc']}" for i, s in enumerate(pool)
    )
    history: list[dict] = []
    results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="arena-adv-") as tmp:
        root = Path(tmp)
        workspaces: dict[str, Path] = {}
        sessions: dict[str, ToolSession] = {}
        previews: dict[str, StaticPreviewServer] = {}

        for phase in phases:
            phase_name = str(phase.get("name") or "phase")
            participants = [p for p in (phase.get("participants") or []) if p != "judge"]
            emit(phase_name, "system", f"phase_start:{phase_name}", "phase_start")
            for role_idx, role in enumerate(participants):
                halted = executor.halted(status_check, deadline)
                if halted:
                    if on_status:
                        on_status(halted)
                    return {}
                model_id = role_to_model.get(role)
                if not model_id:
                    continue
                first = role not in workspaces
                work = workspaces.get(role) or (root / f"work_{role}")
                work.mkdir(exist_ok=True)
                workspaces[role] = work
                if first:
                    mount_skills(work, pool)
                    (work / "TARGET.md").write_text(str(target_code), encoding="utf-8")
                    tests_dir = work / "tests"
                    tests_dir.mkdir(exist_ok=True)
                    (tests_dir / "test_target.py").write_text(str(test_code), encoding="utf-8")
                if phase.get("inputs") or format_config.get("share_opponent"):
                    _copy_opponent(work, workspaces, role)
                mission = _mission(format_config, role)
                (work / "README.md").write_text(
                    f"# {format_name}\nRole: {role}\n{mission}\n"
                    f"Pick {pick_n} skills, TOOL read each SKILL.md, write files, TOOL test.\n",
                    encoding="utf-8",
                )
                sess = sessions.get(role) or ToolSession(work, root=work, tool_timeout=tool_timeout)
                sessions[role] = sess

                preview_url = ""
                if first and _want_preview(format_config):
                    try:
                        server = StaticPreviewServer(workdir=work, port=port_for_index(role_idx))
                        server.start()
                        previews[role] = server
                        preview_url = f"http://localhost:{port_for_index(role_idx)}"
                        emit_action(phase_name, model_id, "preview", target=preview_url, state="starting", result="preview up")
                    except Exception as exc:
                        emit_action(phase_name, model_id, "preview", state="failed", result=str(exc))

                chosen_skills: list[str] = []
                theory = ""
                nudged = False
                for turn in range(max_turns):
                    halted = executor.halted(status_check, deadline)
                    if halted:
                        break
                    prior = "\n".join(
                        f"[{a['phase']}/{a['model_id']}]: {a['artifact'][:500]}"
                        for a in history[-5:]
                    )
                    opponent = " ".join(r for r in participants if r != role)
                    system_prompt = (
                        f"You are {role} in '{format_name}'.\n"
                        f"Mission: {mission}\n"
                        f"Opponent roles: {opponent or '(none)'}.\n"
                        f"SKILLS POOL (pick {pick_n}):\n{skill_list_text}\n"
                        "Tools (one per line, body tools need END_TOOL):\n"
                        "TOOL read path=... | TOOL ls [path=...] | TOOL write path=... END_TOOL | "
                        "TOOL run path=... END_TOOL | TOOL shell cmd='...' | TOOL install cmd='...' | "
                        "TOOL grep pattern=... [path=...] | TOOL tree [path=...] | TOOL cp from=... to=... | "
                        "TOOL mv from=... to=... | TOOL rm path=... | TOOL fetch url=... | "
                        "TOOL bg name=... END_TOOL | TOOL ps | TOOL kill name=... | TOOL logs name=... | "
                        "TOOL use_skill name=... | TOOL skills list | TOOL test | DONE\n"
                        f"Rules: max {max_steps} tool steps, {max_turns} turns.\n"
                        f"You MUST emit SKILLS: a,b,... ({pick_n} names) then TOOL use_skill "
                        "name=<skill> for each chosen skill before writing solution files.\n"
                        "Write THEORY.md. Modify workspace files. Run TOOL test "
                        "(harness is tests/test_target.py; do not fake TEST_PASS).\n"
                        "Plain prose is not a successful turn. Emit TOOL calls.\n"
                        f"Prior: {prior or '(none)'}"
                    )
                    user_prompt = (
                        f"Workdir files:\n{sess.ls()}\n\nTARGET:\n{str(target_code)[:2000]}\n\n"
                        f"Your turn {turn + 1}/{max_turns}, steps {sess.steps}/{max_steps}. Emit TOOL calls."
                    )
                    try:
                        content = client.model(
                            battle_id,
                            model_id,
                            [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            phase=phase_name,
                            max_tokens=race_tokens,
                        ).strip()
                    except Exception as exc:
                        emit_action(
                            phase_name,
                            model_id,
                            "model",
                            state="failed",
                            result=str(exc)[:4000],
                        )
                        break
                    calls = parse_tool_calls(content)
                    if not calls:
                        if not nudged:
                            nudged = True
                            emit_action(
                                phase_name,
                                model_id,
                                "nudge",
                                result="No TOOL calls; prose is not execution. Emit TOOL calls.",
                            )
                            continue
                        emit_action(phase_name, model_id, "nudge", result="Still no TOOL calls; skipping turn.")
                        continue
                    done_this_role = False
                    for call in calls:
                        if sess.steps >= max_steps:
                            done_this_role = True
                            break
                        if call.get("tool") == "skills":
                            pool_names = {s["name"] for s in pool}
                            chosen_skills = [
                                c for c in call.get("chosen", [])[:5] if c in pool_names
                            ]
                        exec_start = time.time()
                        exec_res = sess.exec_tool(call)
                        exec_ms = int((time.time() - exec_start) * 1000)
                        exec_res_sanitized = sanitize_artifact(exec_res[:10000])
                        emit_action(
                            phase_name,
                            model_id,
                            call.get("tool", "?"),
                            target=call.get("path") or call.get("name") or call.get("url") or "",
                            state="done",
                            duration_ms=exec_ms,
                            result=exec_res_sanitized[:4000],
                        )
                        history.append(
                            {
                                "phase": phase_name,
                                "model_id": model_id,
                                "artifact": exec_res_sanitized,
                                "role": role,
                            }
                        )
                        if call.get("tool") == "done":
                            done_this_role = True
                            break
                    if done_this_role:
                        break

                files = _collect_files(work)
                try:
                    theory = (work / "THEORY.md").read_text()[:5000]
                except Exception:
                    theory = ""
                test_res = sess.test("")
                passed = (
                    "TEST_PASS" in test_res
                    and "rc=0" in test_res
                    and bool(sess.wrote_paths)
                    and sess.ran_test
                )
                skill_read_ok = bool(chosen_skills) and set(chosen_skills).issubset(sess.skill_reads)
                if not skill_read_ok:
                    passed = False
                outcome = "TEST_PASS" if passed else "TEST_FAIL"
                result = {
                    "model_id": model_id,
                    "role": role,
                    "outcome": executor.guard(
                        outcome,
                        format_config.get("outcome_markers", []),
                        default=outcome,
                    ),
                    "passed": passed,
                    "steps": sess.steps,
                    "files": files,
                    "chosen_skills": chosen_skills,
                    "theory": theory,
                    "skill_read_ok": skill_read_ok,
                    "preview_url": preview_url,
                    "phase": phase_name,
                }
                executor.emit_result(client, battle_id, phase_name, result)
                files_json = json.dumps(
                    {
                        "files": files,
                        "chosen_skills": chosen_skills,
                        "theory": theory,
                        "outcome": outcome,
                        "steps": sess.steps,
                        "skill_read_ok": skill_read_ok,
                        "preview_url": preview_url,
                    },
                    indent=2,
                )
                client.round(
                    battle_id,
                    phase_name,
                    model_id,
                    sanitize_artifact(files_json),
                    event_type="artifact",
                    sequence=seq["n"] + 1,
                )
                seq["n"] += 1
                history.append(
                    {
                        "phase": phase_name,
                        "model_id": model_id,
                        "artifact": sanitize_artifact(files_json),
                        "role": role,
                    }
                )
                results.append(result)

        for server in previews.values():
            try:
                server.stop()
            except Exception:
                pass

    try:
        winner = None
        if results:
            sorted_res = sorted(
                results,
                key=lambda x: (x.get("passed", False), -x.get("steps", 999)),
                reverse=True,
            )
            winner = sorted_res[0]
            for r in results:
                delta = 5 if r is winner else -5
                for chosen in r.get("chosen_skills", [])[:5]:
                    for s in SKILL_POOL:
                        if s["name"] == chosen:
                            s["elo"] = max(800, min(2000, s["elo"] + delta))
    except Exception:
        pass

    for r in results:
        history.append(
            {
                "phase": r.get("phase") or "race",
                "model_id": r["model_id"],
                "artifact": (
                    f"RESULT {r['outcome']} chosen {r['chosen_skills']} "
                    f"passed={r['passed']} steps={r['steps']} "
                    f"theory={(r.get('theory', '')[:200])}"
                ),
                "role": r["role"],
            }
        )

    try:
        return executor.finish(
            client=client,
            battle_id=battle_id,
            format_config=format_config,
            history=history,
            on_status=on_status,
        )
    except Exception as exc:
        emit("judge", "system", f"judge failed: {exc}", "error")
        scores = {
            r["model_id"]: (80.0 if r.get("passed") else 20.0) for r in results if r.get("model_id")
        }
        if on_status:
            on_status("completed")
        return scores
