"""Shared harness helpers used by bespoke format executors."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
_CODE_START_RE = re.compile(
    r"^(?:import\s|from\s|def\s|class\s|@|#!)",
)


def run_python(
    path: Path,
    cwd: Path,
    timeout: int,
    args: list[str] | None = None,
    env: dict | None = None,
) -> tuple[str, str, int]:
    """Run a python script; returns (stdout, stderr, returncode). Never raises."""
    try:
        proc = subprocess.run(
            ["python3", str(path), *(args or [])],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.stdout[:50000], proc.stderr[:20000], proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = ""
        if exc.stdout is not None:
            out = (
                exc.stdout.decode(errors="ignore")
                if isinstance(exc.stdout, bytes)
                else str(exc.stdout)
            )
        err = "timeout"
        if exc.stderr is not None:
            err = (
                exc.stderr.decode(errors="ignore")
                if isinstance(exc.stderr, bytes)
                else str(exc.stderr)
            )
        return out[:50000], f"timeout after {timeout}s\n{err}"[:20000], -1
    except Exception as exc:  # noqa: BLE001
        return "", str(exc)[:20000], -1


def _ast_ok(source: str) -> bool:
    s = source.strip()
    if not s:
        return False
    try:
        ast.parse(s)
    except SyntaxError:
        return False
    return True


def _scan_contiguous_code(text: str) -> str | None:
    lines = text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if _CODE_START_RE.match(line.strip()):
            start = i
            break
    if start is None:
        return None
    collected: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if collected and stripped and not line.startswith((" ", "\t")):
            if not _CODE_START_RE.match(stripped) and not stripped.startswith(
                ("#", ")", "]", "}", "else:", "elif ", "except", "finally:", "try:", "with ", "if ", "for ", "while ", "return ", "yield ", "raise ", "pass", "break", "continue", "global ", "nonlocal ", "assert ", "del ", "async ", "await ")
            ):
                if re.match(r"^[A-Za-z].*[.?!]$", stripped) or stripped.lower().startswith(
                    ("let me", "i ", "the ", "this ", "here ", "output ", "protocol")
                ):
                    break
        collected.append(line)
    candidate = "\n".join(collected).strip()
    return candidate if _ast_ok(candidate) else None


def extract_python_source(text: str) -> str | None:
    """Extract valid Python from a model reply; None if nothing parses."""
    if not text or not str(text).strip():
        return None
    t = str(text).strip()

    fences = _FENCE_RE.findall(t)
    for body in reversed(fences):
        candidate = body.strip()
        if _ast_ok(candidate):
            return candidate

    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
        if _ast_ok(candidate):
            return candidate

    if _ast_ok(t):
        return t

    return _scan_contiguous_code(t)


def strip_fences(text: str) -> str:
    """Best-effort code extraction; empty string if nothing valid."""
    extracted = extract_python_source(text)
    if extracted is not None:
        return extracted
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return t


def model_code(client, battle_id, model_id, phase, messages) -> str:
    """Call the model and extract Python source (empty if invalid)."""
    raw = client.model(battle_id, model_id, messages, phase=phase)
    return extract_python_source(raw) or ""


def write_assets(workdir: Path, assets: dict[str, str]) -> None:
    for relpath, content in assets.items():
        p = workdir / relpath
        if relpath.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def read_outcome(stdout: str, default: str = "INCONCLUSIVE") -> str:
    """Parse the final 'OUTCOME: <TOKEN>' line a harness prints."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("OUTCOME:"):
            return line.split(":", 1)[1].strip()
    return default
