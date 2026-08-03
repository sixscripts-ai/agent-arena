# Redact Policy

From backend/agent_arena/redact.py

- REDACT_PATTERNS list of regex for secrets: sk-, sk-or-v1-, sk-Ke, wk-, ws-, gsk_, xai-, mg__, standard_, ak-, as-
- sanitize_artifact(text, max_bytes=100_000): redact + utf-8 truncate
- Every client.round artifact must go through sanitize_artifact()
