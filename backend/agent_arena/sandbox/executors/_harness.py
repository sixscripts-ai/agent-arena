"""Shared harness helpers used by bespoke format executors."""

from __future__ import annotations

import subprocess
from pathlib import Path


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


def strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines)
    return t


def model_code(client, battle_id, model_id, phase, messages) -> str:
    """Call the model and strip markdown fences."""
    return strip_fences(client.model(battle_id, model_id, messages, phase=phase))


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
