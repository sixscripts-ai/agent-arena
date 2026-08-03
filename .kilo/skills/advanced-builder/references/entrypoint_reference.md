# Entrypoint Reference

From backend/agent_arena/sandbox/entrypoint.py

- main(battle_id): reads BACKEND_PUBLIC_URL, INTERNAL_API_KEY, BATTLE_BOOTSTRAP_JSON from env
- If missing bootstrap, exit 2
- Parses json, creates HttpTransport + InternalClient, run_battle_loop
- Must set os.environ["ARENA_IN_SANDBOX"] = "1" at very top of main() before client creation - this is flag checked by AdvancedExecutor gate
