from __future__ import annotations

FORMAT_EXECUTORS: dict[str, type] = {}


def register(cls, *names: str) -> None:
    for name in names:
        FORMAT_EXECUTORS[name] = cls


from . import advanced as _advanced  # noqa: E402,F401
