from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import InternalClient


class Executor:
    def run_phase(
        self,
        *,
        client: "InternalClient",
        battle_id: str,
        phase: dict,
        role_to_model: dict[str, str],
        history: list[dict],
        format_config: dict,
        round_visibility: str,
    ) -> list[dict[str, Any]]:
        """Execute one phase; return list of artifact dicts."""
        raise NotImplementedError
