"""Modal Sandbox entrypoint: drive battle via HTTP internal API."""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main(battle_id: str) -> None:
    os.environ["ARENA_IN_SANDBOX"] = "1"
    base = os.environ["BACKEND_PUBLIC_URL"].rstrip("/")
    key = os.environ["INTERNAL_API_KEY"]
    bootstrap = os.environ.get("BATTLE_BOOTSTRAP_JSON")
    if not bootstrap:
        print("missing BATTLE_BOOTSTRAP_JSON", file=sys.stderr)
        sys.exit(2)
    data = json.loads(bootstrap)
    from agent_arena.sandbox.client import HttpTransport, InternalClient
    from agent_arena.sandbox.runner import run_battle_loop

    client = InternalClient(HttpTransport(base, key))
    statuses: list[str] = []

    def on_status(status: str) -> None:
        statuses.append(status)
        try:
            client.round(battle_id, "system", "system", status, event_type="battle_status")
        except Exception:
            pass

    run_battle_loop(
        battle_id=battle_id,
        format_config=data["format_config"],
        model_ids=data["model_ids"],
        round_visibility=data.get("round_visibility", "isolated"),
        timeout_seconds=int(data.get("timeout_seconds") or 600),
        client=client,
        on_status=on_status,
    )


if __name__ == "__main__":
    main(sys.argv[1])
