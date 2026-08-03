# Sandbox Gates — Required Checks

## Hard Gate
```python
if os.environ.get("ARENA_IN_SANDBOX") != "1":
    raise RuntimeError("Not in sandbox")
```
Must be at top of run_phase and tool_session run().

## ToolSession

Root: `arena-tools-<battle_id>-<model>` under /tmp or ./arena-tools.
_resolve:
```python
def _resolve(self, rel):
    p = (self.root / rel).resolve()
    if ".." in Path(rel).parts: raise ValueError("ERROR: path traversal")
    if not str(p).startswith(str(self.root.resolve())): raise ValueError("ERROR: outside root")
    return p
```

Popen:
```python
proc = subprocess.Popen(["python3", str(path)], stdout=PIPE, stderr=PIPE, start_new_session=True)
try: out,_ = proc.communicate(timeout=15)
except TimeoutExpired:
    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    out = b"[TIMEOUT]"
```

Cap 50KB:
```
if len(out) > 50*1024: out = out[:50*1024] + b"\n[TRUNCATED]"
```

Sanitize every artifact:
```
sanitized = sanitize_artifact(raw)
client.round(battle_id, phase, model_id, sanitized, event_type="artifact")
```

## Evaluations

- eval-tool-escape.md: Test ../../etc/passwd, /etc/passwd, absolute path /tmp traversal.
- eval-timeout-kill.md: while True: pass must be killed.
- eval-sandbox-gate.md: unset env var must RuntimeError.
