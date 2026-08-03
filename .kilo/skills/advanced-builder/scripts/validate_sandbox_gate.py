from __future__ import annotations
import pathlib

def check():
    for path in [
        pathlib.Path("/Users/villain/modal/backend/agent_arena/sandbox/executors/advanced_executor.py"),
        pathlib.Path("backend/agent_arena/sandbox/executors/advanced_executor.py"),
    ]:
        if path.exists():
            txt = path.read_text()
            if 'ARENA_IN_SANDBOX' in txt and 'RuntimeError' in txt:
                print(f"OK {path} has sandbox gate")
            else:
                print(f"FAIL {path} missing gate")
        else:
            print(f"Skip {path} not found")

    ep = pathlib.Path("/Users/villain/modal/backend/agent_arena/sandbox/entrypoint.py")
    if ep.exists() and 'ARENA_IN_SANDBOX' in ep.read_text():
        print(f"OK {ep} sets ARENA_IN_SANDBOX=1")
    else:
        print(f"FAIL {ep}")

if __name__ == "__main__":
    check()
