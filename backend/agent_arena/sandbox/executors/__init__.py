from .build_and_break import BuildAndBreakExecutor
from .scripted import ScriptedExecutor
from .formats import FORMAT_EXECUTORS

_ENGINE_REGISTRY = {
    "build_and_break": BuildAndBreakExecutor,
    "script_vs_defense": ScriptedExecutor,
    "high_complexity": ScriptedExecutor,
}


def get_executor(format_config: dict):
    """Resolve a bespoke format executor (name, then slug), else engine fallback."""
    name = format_config.get("name") or ""
    cls = FORMAT_EXECUTORS.get(name)
    if cls is not None:
        return cls()
    slug = format_config.get("id") or format_config.get("slug") or ""
    cls = FORMAT_EXECUTORS.get(slug)
    if cls is not None:
        return cls()
    engine = format_config.get("engine", "scripted")
    return _ENGINE_REGISTRY.get(engine, ScriptedExecutor)()
