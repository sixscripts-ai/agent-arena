# OWASP Mapped to Agent Arena

## 1. Broken Access Control
- File: `battles.py:47 _get_owned` must guard every battle read/write.
- `providers.py` list only own + host. Validate model_id ownership in _validate_model_ids.
- Host ids `host:` bypass must be allowlisted in `is_host_model`.

## 2. Cryptographic Failures
- `crypto.py`: Fernet, key from ENCRYPTION_KEY env, no hardcoding.
- Masked key: show last 4 only, not full length.
- Appwrite field `encrypted_key` never returned (filtered in get_battle).

## 3. Injection
- Prompt injection: judge_prompts.md rubrics user-influenced? Format config json loads safely (no eval).
- No SQL, but NoSQL via Appwrite queries must use Query.equal not string concat.

## 4. Insecure Design
- MAX_ACTIVE_BATTLES=5 anti-abuse.
- timeout_seconds enforced + deadline halted().
- Sandbox launcher stop_sandbox on cancel.

## 5. Security Misconfig
- CORS: explicit origins + regex for *.vercel.app, not *.
- Modal internal_router under /internal must require INTERNAL_TOKEN.

## 6. Vulnerable Components
- FastAPI, Appwrite SDK, pnpm npm audit.

## 7. Auth Failures
- get_current_user verifies JWT via Appwrite, not custom decode.
- JWT refresh every 10min with interval cleanup.

## 8. Data Integrity
- event_bus event_id UUID, created_at sorted, dedup prevents replay.
- EXECUTOR_RESULT JSON parse with guard markers ESCAPE_OK etc.

## 9. Logging / Monitoring
- redact.py sanitize_artifact removes keys, tokens, api_key, Bearer.
- No PII logging.

## 10. SSRF
- providers health endpoint base_url user-controlled → validate scheme https only, block 169.254/10./127.0.0.1, timeout 5s.
