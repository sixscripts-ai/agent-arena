"""Bespoke per-format executor registry.

Keyed by canonical format name (collision-proof; `seed_formats._slugify`
truncates slugs to 36 chars) AND by slug. `get_executor` checks name first,
then slug, then engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import Executor

from .rev_shell_vs_defense import (
    NAME as _NAME_4,
    SLUG as _SLUG_4,
    RevShellVsDefenseExecutor,
)

FORMAT_EXECUTORS: dict[str, "type[Executor]"] = {}


def register(cls: "type[Executor]", name: str, slug: str) -> None:
    FORMAT_EXECUTORS[name] = cls
    FORMAT_EXECUTORS[slug] = cls


register(RevShellVsDefenseExecutor, _NAME_4, _SLUG_4)
