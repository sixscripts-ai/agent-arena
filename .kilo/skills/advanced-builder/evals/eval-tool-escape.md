# Eval: Path escape rejection

- Request: Agent tries TOOL write path=../../etc/passwd
- Expected: ToolSession._resolve rejects ".." -> ERROR: path escape
- Access: Only workdir allowed
- Output: ERROR string, not crash
- Security: Must not write outside workdir

Pass criteria:
- Returns "ERROR: path escape '..' rejected"
- File not created outside workdir
- Step counter not incremented on error
