"""Format-driven universal battle loop for AdvancedExecutor."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .advanced_executor import (
    RACE_MAX_TOKENS,
    SKILL_POOL,
    ToolSession,
    select_skills,
)
from .preview import StaticPreviewServer, port_for_index, preview_enabled
from .skill_pool import load_skill_pool, mount_skills
from ...model_protocol import (
    classify_provider_error,
    excerpt,
    model_capabilities,
    model_result_from_payload,
    native_tool_schemas,
    normalize_tool_calls,
    repair_prompt,
)
from ...redact import sanitize_artifact

MAX_NO_TOOL = 2
MAX_WORKERS = 2


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


def _target_of(call: dict) -> str:
    return str(
        call.get("path")
        or call.get("name")
        or call.get("url")
        or call.get("cmd")
        or ""
    )


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
    seq_lock = threading.Lock()
    history: list[dict] = []
    history_lock = threading.Lock()
    results: list[dict] = []
    results_lock = threading.Lock()
    native_tools = native_tool_schemas()

    def emit(phase, model_id, artifact, event_type="artifact"):
        with seq_lock:
            seq["n"] += 1
            n = seq["n"]
        client.round(
            battle_id,
            phase,
            model_id,
            artifact,
            event_type=event_type,
            sequence=n,
        )

    def emit_action(phase, model_id, action, target="", state="", duration_ms=0, result=""):
        emit(
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
            "action_log",
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
    pool_names = {s["name"] for s in pool}

    emit(
        "init",
        "system",
        json.dumps(
            {
                "executor": "AdvancedExecutor",
                "format_engine": format_config.get("engine") or "universal",
                "universal": True,
            }
        ),
        "runtime_selected",
    )

    all_roles: list[str] = []
    for phase in phases:
        for role in phase.get("participants") or []:
            if role != "judge" and role not in all_roles:
                all_roles.append(role)

    with tempfile.TemporaryDirectory(prefix="arena-adv-") as tmp:
        root = Path(tmp)
        workspaces: dict[str, Path] = {}
        sessions: dict[str, ToolSession] = {}
        previews: dict[str, StaticPreviewServer] = {}
        preview_urls: dict[str, str] = {}

        for role_idx, role in enumerate(all_roles):
            model_id = role_to_model.get(role)
            if not model_id:
                continue
            work = root / f"work_{role}"
            work.mkdir(exist_ok=True)
            workspaces[role] = work
            mount_skills(work, pool)
            (work / "TARGET.md").write_text(str(target_code), encoding="utf-8")
            tests_dir = work / "tests"
            tests_dir.mkdir(exist_ok=True)
            (tests_dir / "test_target.py").write_text(str(test_code), encoding="utf-8")
            mission = _mission(format_config, role)
            (work / "README.md").write_text(
                f"# {format_name}\nRole: {role}\n{mission}\n"
                f"Pick {pick_n} skills, use_skill each SKILL.md, write files, test.\n",
                encoding="utf-8",
            )
            sess = ToolSession(work, root=work, tool_timeout=tool_timeout)
            sessions[role] = sess
            listing = sess.ls()
            emit_action("init", model_id, "ls", target=".", state="done", result=listing)
            if _want_preview(format_config):
                try:
                    server = StaticPreviewServer(workdir=work, port=port_for_index(role_idx))
                    server.start()
                    previews[role] = server
                    preview_url = f"http://localhost:{port_for_index(role_idx)}"
                    preview_urls[role] = preview_url
                    sess.preview_url = preview_url
                    emit_action(
                        "init",
                        model_id,
                        "preview",
                        target=preview_url,
                        state="starting",
                        result="preview up",
                    )
                except Exception as exc:
                    emit_action("init", model_id, "preview", state="failed", result=str(exc))

        def run_participant(phase: dict, phase_name: str, role: str, participants: list[str]) -> None:
            halted = executor.halted(status_check, deadline)
            if halted:
                return
            model_id = role_to_model.get(role)
            if not model_id:
                return
            work = workspaces[role]
            sess = sessions[role]
            if phase.get("inputs") or format_config.get("share_opponent"):
                _copy_opponent(work, workspaces, role)
            mission = _mission(format_config, role)
            caps = model_capabilities(model_id)
            use_native = bool(caps.get("supports_tools"))
            tools_payload = native_tools if use_native else None
            preview_url = preview_urls.get(role, "")
            emit(
                phase_name,
                model_id,
                json.dumps({"role": role, "model_id": model_id}),
                "participant_start",
            )
            opponent = " ".join(r for r in participants if r != role)
            system_prompt = (
                f"You are {role} in '{format_name}'.\n"
                f"Mission: {mission}\n"
                f"Opponent roles: {opponent or '(none)'}.\n"
                f"SKILLS POOL (pick {pick_n}):\n{skill_list_text}\n"
                "Use native function tools when provided: ls, read, write, patch, shell, "
                "install, fetch, test, use_skill, preview, skills.\n"
                "Fallback text: TOOL read path=... | TOOL write path=... END_TOOL | "
                "TOOL test | TOOL use_skill name=... | SKILLS: a,b,c | DONE\n"
                f"Rules: max {max_steps} tool steps, {max_turns} turns.\n"
                f"You MUST choose {pick_n} skills and call use_skill for each before writing solution files.\n"
                "Read TARGET.md. Write THEORY.md and solution files. Run test. "
                "Plain prose is not a successful turn.\n"
            )
            messages: list[dict] = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Workdir files:\n{sess.ls()}\n\nTARGET:\n{str(target_code)[:2000]}\n\n"
                        f"Start. Call tools. Turn 1/{max_turns}."
                    ),
                },
            ]
            chosen_skills: list[str] = []
            consecutive_empty = 0
            failed_reason: str | None = None
            for turn in range(max_turns):
                halted = executor.halted(status_check, deadline)
                if halted:
                    failed_reason = halted
                    break
                emit(
                    phase_name,
                    model_id,
                    json.dumps({"model_id": model_id, "turn": turn + 1}),
                    "model_request",
                )
                t0 = time.time()
                try:
                    raw = client.model_result(
                        battle_id,
                        model_id,
                        messages,
                        phase=phase_name,
                        max_tokens=race_tokens,
                        tools=tools_payload,
                        tool_choice="auto" if tools_payload else None,
                    )
                except Exception as exc:
                    latency_ms = int((time.time() - t0) * 1000)
                    kind = classify_provider_error(exc) or "provider_error"
                    emit(
                        phase_name,
                        model_id,
                        json.dumps(
                            {
                                "provider": None,
                                "model": model_id,
                                "finish_reason": kind,
                                "content_length": 0,
                                "native_tool_call_count": 0,
                                "normalized_tool_call_count": 0,
                                "parse_error": kind,
                                "latency_ms": latency_ms,
                            }
                        ),
                        "model_response",
                    )
                    emit_action(phase_name, model_id, "model", state="failed", result=kind)
                    failed_reason = kind
                    break
                latency_ms = int((time.time() - t0) * 1000)
                result = model_result_from_payload(raw)
                calls, parse_error = normalize_tool_calls(result)
                diag = {
                    "provider": result.provider,
                    "model": result.model or model_id,
                    "finish_reason": result.finish_reason,
                    "content_length": len(result.content or ""),
                    "native_tool_call_count": len(result.tool_calls or []),
                    "normalized_tool_call_count": len(calls),
                    "parse_error": parse_error,
                    "latency_ms": latency_ms,
                }
                if parse_error:
                    diag["excerpt"] = excerpt(result.content)
                emit(phase_name, model_id, json.dumps(diag), "model_response")
                assistant: dict = {
                    "role": "assistant",
                    "content": result.content if result.content else None,
                }
                if result.tool_calls:
                    assistant["tool_calls"] = result.tool_calls
                messages.append(assistant)
                executable = [c for c in calls if c.get("tool") and c.get("tool") != "error"]
                if not executable:
                    consecutive_empty += 1
                    if consecutive_empty < MAX_NO_TOOL:
                        repair = repair_prompt()
                        emit_action(
                            phase_name,
                            model_id,
                            "nudge",
                            result="No TOOL calls; prose is not execution. Emit TOOL calls.",
                        )
                        messages.append({"role": "user", "content": repair})
                        continue
                    failed_reason = "no_tool_exhaustion"
                    emit(
                        phase_name,
                        model_id,
                        json.dumps({"role": role, "reason": failed_reason}),
                        "participant_failed",
                    )
                    emit_action(
                        phase_name,
                        model_id,
                        "nudge",
                        result="Still no TOOL calls; participant failed.",
                    )
                    break
                consecutive_empty = 0
                done_this_role = False
                for idx, call in enumerate(executable):
                    if sess.steps >= max_steps:
                        done_this_role = True
                        break
                    if call.get("tool") == "skills":
                        chosen_skills = [
                            c for c in call.get("chosen", [])[:5] if c in pool_names
                        ]
                    if call.get("tool") == "use_skill":
                        name = str(call.get("name") or "")
                        if name in pool_names and name not in chosen_skills:
                            chosen_skills.append(name)
                    emit(
                        phase_name,
                        model_id,
                        json.dumps({"tool": call.get("tool"), "id": call.get("id") or ""}),
                        "tool_start",
                    )
                    exec_start = time.time()
                    exec_res = sess.exec_tool(call)
                    exec_ms = int((time.time() - exec_start) * 1000)
                    exec_res_sanitized = sanitize_artifact(exec_res[:10000])
                    call_id = str(call.get("id") or f"call_{turn}_{idx}")
                    emit(
                        phase_name,
                        model_id,
                        json.dumps(
                            {
                                "tool": call.get("tool"),
                                "id": call_id,
                                "result": exec_res_sanitized[:2000],
                            }
                        ),
                        "tool_result",
                    )
                    emit_action(
                        phase_name,
                        model_id,
                        call.get("tool", "?"),
                        target=_target_of(call),
                        state="done",
                        duration_ms=exec_ms,
                        result=exec_res_sanitized[:4000],
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": call.get("tool") or "",
                            "content": exec_res_sanitized,
                        }
                    )
                    with history_lock:
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
            if failed_reason:
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
                "failed_reason": failed_reason,
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
            emit(phase_name, model_id, sanitize_artifact(files_json), "artifact")
            with history_lock:
                history.append(
                    {
                        "phase": phase_name,
                        "model_id": model_id,
                        "artifact": sanitize_artifact(files_json),
                        "role": role,
                    }
                )
            with results_lock:
                results.append(result)
            if failed_reason and failed_reason != "no_tool_exhaustion":
                emit(
                    phase_name,
                    model_id,
                    json.dumps({"role": role, "reason": failed_reason}),
                    "participant_failed",
                )
            elif not failed_reason:
                emit(
                    phase_name,
                    model_id,
                    json.dumps({"role": role, "passed": passed}),
                    "participant_completed",
                )

        def _safe_participant(phase, phase_name, role, participants):
            try:
                run_participant(phase, phase_name, role, participants)
            except Exception as exc:
                mid = role_to_model.get(role) or "system"
                emit(
                    phase_name,
                    mid,
                    json.dumps({"role": role, "reason": str(exc)[:500]}),
                    "participant_failed",
                )

        for phase in phases:
            phase_name = str(phase.get("name") or "phase")
            participants = [p for p in (phase.get("participants") or []) if p != "judge"]
            emit(phase_name, "system", f"phase_start:{phase_name}", "phase_start")
            halted = executor.halted(status_check, deadline)
            if halted:
                if on_status:
                    on_status(halted)
                return {}
            workers = min(MAX_WORKERS, max(1, len(participants)))
            with ThreadPoolExecutor(max_workers=workers) as pool_ex:
                futs = [
                    pool_ex.submit(_safe_participant, phase, phase_name, role, participants)
                    for role in participants
                ]
                for fut in as_completed(futs):
                    fut.result()

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
