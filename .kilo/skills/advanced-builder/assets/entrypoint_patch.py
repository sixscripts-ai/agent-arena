# Add at top of main() in backend/agent_arena/sandbox/entrypoint.py
import os
os.environ["ARENA_IN_SANDBOX"] = "1"
