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

from .payload_vs_detection import (
    NAME as _NAME_5,
    SLUG as _SLUG_5,
    PayloadVsDetectionExecutor,
)

from .polymorph_vs_signature import (
    NAME as _NAME_16,
    SLUG as _SLUG_16,
    PolymorphVsSignatureExecutor,
)

from .cred_reuse_vs_hardening import (
    NAME as _NAME_17,
    SLUG as _SLUG_17,
    CredReuseVsHardeningExecutor,
)

from .arms_race import (
    NAME as _NAME_11,
    SLUG as _SLUG_11,
    ArmsRaceExecutor,
)

from .exploit_vs_patch import (
    NAME as _NAME_19,
    SLUG as _SLUG_19,
    ExploitVsPatchExecutor,
)

from .time_limited_siege import (
    NAME as _NAME_20,
    SLUG as _SLUG_20,
    TimeLimitedSiegeExecutor,
)

from .digital_twin import (
    NAME as _NAME_21,
    SLUG as _SLUG_21,
    DigitalTwinExecutor,
)

from .same_defense_adaptive import (
    NAME as _NAME_25,
    SLUG as _SLUG_25,
    SameDefenseAdaptiveExecutor,
)

FORMAT_EXECUTORS: dict[str, "type[Executor]"] = {}


def register(cls: "type[Executor]", name: str, slug: str) -> None:
    FORMAT_EXECUTORS[name] = cls
    FORMAT_EXECUTORS[slug] = cls


register(RevShellVsDefenseExecutor, _NAME_4, _SLUG_4)
register(PayloadVsDetectionExecutor, _NAME_5, _SLUG_5)
register(PolymorphVsSignatureExecutor, _NAME_16, _SLUG_16)
register(CredReuseVsHardeningExecutor, _NAME_17, _SLUG_17)
register(ArmsRaceExecutor, _NAME_11, _SLUG_11)
register(ExploitVsPatchExecutor, _NAME_19, _SLUG_19)
register(TimeLimitedSiegeExecutor, _NAME_20, _SLUG_20)
register(DigitalTwinExecutor, _NAME_21, _SLUG_21)
register(SameDefenseAdaptiveExecutor, _NAME_25, _SLUG_25)
