"""Load battle skill bodies from .agents/skills (or ARENA_SKILLS_ROOT)."""

from __future__ import annotations

import os
import re
from pathlib import Path

BATTLE_SKILL_NAMES = (
    "secure-code-execution",
    "sandbox-runtime-engineer",
    "artifact-workspace-versioning",
    "realtime-execution-streaming",
    "battle-runtime-observability",
    "terminal-sandbox-ui",
    "python-kata-fixer",
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def skills_root() -> Path:
    env = os.environ.get("ARENA_SKILLS_ROOT", "").strip()
    if env:
        return Path(env)
    mounted = Path("/opt/arena-skills")
    if mounted.is_dir():
        return mounted
    return Path(__file__).resolve().parents[4] / ".agents" / "skills"


def _parse_frontmatter(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return meta
    key = None
    buf: list[str] = []
    for line in m.group(1).splitlines():
        if key and (line.startswith(" ") or line.startswith("\t")):
            buf.append(line.strip())
            continue
        if key:
            meta[key] = " ".join(buf).strip().strip("\"'")
        key = None
        buf = []
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        val = v.strip()
        if val in (">", ">-", "|"):
            buf = []
        else:
            meta[key] = val.strip("\"'")
            key = None
    if key:
        meta[key] = " ".join(buf).strip().strip("\"'")
    return meta


def load_skill_pool(root: Path | None = None) -> list[dict]:
    base = root or skills_root()
    pool: list[dict] = []
    for name in BATTLE_SKILL_NAMES:
        path = base / name / "SKILL.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta = _parse_frontmatter(text)
        desc = (meta.get("description") or "").strip() or f"Skill {name}"
        if len(desc) > 240:
            desc = desc[:237] + "..."
        pool.append(
            {
                "name": meta.get("name") or name,
                "desc": desc,
                "elo": 1200,
                "path": str(path),
                "body": text,
            }
        )
    return pool


def mount_skills(dest: Path, pool: list[dict]) -> Path:
    """Copy skill bodies into a participant workspace (read-only copies)."""
    skills_dir = dest / ".agents" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for s in pool:
        d = skills_dir / s["name"]
        d.mkdir(parents=True, exist_ok=True)
        target = d / "SKILL.md"
        target.write_text(s.get("body") or f"# {s['name']}\n{s['desc']}\n", encoding="utf-8")
        try:
            target.chmod(0o444)
        except OSError:
            pass
    return skills_dir
