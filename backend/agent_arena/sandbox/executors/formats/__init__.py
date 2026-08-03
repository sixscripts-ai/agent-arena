"""Bespoke per-format executor registry.

Keyed by canonical format name (collision-proof; `seed_formats._slugify`
truncates slugs to 36 chars) AND by slug. `get_executor` checks name first,
then slug, then engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import Executor

FORMAT_EXECUTORS: dict[str, "type[Executor]"] = {}


def register(cls: "type[Executor]", name: str, slug: str) -> None:
    FORMAT_EXECUTORS[name] = cls
    FORMAT_EXECUTORS[slug] = cls
