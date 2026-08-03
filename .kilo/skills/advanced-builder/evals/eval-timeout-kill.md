# Eval: Run timeout kills process group

- Request: TOOL run with infinite loop `while True: pass`
- Expected: Popen start_new_session=True + killpg SIGKILL after 15s -> TIMEOUT message
- Failure if: Process leaks, no TIMEOUT, hangs, child processes survive

Pass criteria:
- Returns "TIMEOUT after 15s"
- rc captured
- No zombie processes left (pg killed)
- Output capped at 50KB
