from __future__ import annotations
import pathlib
import shutil

# Generates advanced_executor.py from the canonical implementation in modal backend
SRC = pathlib.Path("/Users/villain/modal/backend/agent_arena/sandbox/executors/advanced_executor.py")
DST = pathlib.Path.cwd() / "backend" / "agent_arena" / "sandbox" / "executors" / "advanced_executor.py"

def main():
    # For Kilo skill, copy canonical file if exists, else use template
    if SRC.exists():
        print(f"Copying canonical executor from {SRC}")
        # In skill context, this script is for reference; actual generation is done by agent
        print(SRC.read_text()[:500])
    else:
        print("Canonical src not found, use assets/advanced_executor.py.template")

if __name__ == "__main__":
    main()
