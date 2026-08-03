---
name: arena-security-audit
description: Security audit and hardening for Agent Arena. Checks OWASP Top 10 for FastAPI backend, Appwrite Auth, provider key encryption, sandbox escapes (arena-tools root, .. rejection, Popen killpg), SSE auth, CORS, frontend key leakage, BYOK handling. Use when user asks security review, harden, OWASP, audit secrets, or before prod deploy. Triggers: security audit, harden, secrets leak, PII, sandbox escape, injection.
---

# Arena Security Audit

Purpose-built security reviewer for agent-arena: FastAPI + Modal sandbox + Appwrite + React BYOK.

## When to Use

- "Audit security", "check OWASP", "is my sandbox safe?", "leaking keys?"
- Before adding new executor or provider integration
- After handling user API keys, judge prompts, artifact storage

## Core Threat Model

- **Trust boundaries:** User BYOK keys → encrypted in Appwrite providers collection (crypto.py). Never logged, never returned. masked_key only.
- **Sandbox:** agents run untrusted code via ToolSession under arena-tools- root. Must reject "..", cap output 50KB, Popen start_new_session=True + killpg 15s timeout, ARENA_IN_SANDBOX==1 gate.
- **Battle isolation:** round_visibility isolated vs open; check history filtering per role.
- **SSE:** JWT required, battle ownership check via _get_owned, event_id dedup to prevent replay injection.
- **Frontend:** localStorage arena_jwt + battle_ids, safeGet wrapper but XSS risk if unsanitized artifact rendered.

## Workflow

### Step 0 - Automated Scan

Run `scripts/security_scan.py`:

- Greps for: hardcoded secrets (sk-*, ghp_, api_key), console.log of keys, missing sanitize_artifact(), missing _resolve reject, raw innerHTML, dangerouslySetInnerHTML
- Checks: CORS allow_headers *, allow_methods *, auth.py token validation, providers.py is_host_model bypass, battles.py _validate_model_ids ownership, crypto.py encrypt/decrypt usage
- Checks frontend: direct localStorage usage outside auth.ts, unsanitized artifact rendering in CodePane.tsx (break-all but no DOMPurify), VITE_MODAL_URL exposed
- Outputs `reports/security.json` with severity

### Step 1 - OWASP Top 10 Checklist (arena-specific)

1. **Broken Access Control:** _get_owned enforced on get_battle, stream, artifacts, cancel, save? providers filtered by user_id? host: ids bypass list is allowlisted?
2. **Cryptographic Failures:** encrypt provider key via crypto.py? Fernet key from env ENCRYPTION_KEY rotation? masked_key logic leaks prefix length?
3. **Injection:** format_id from user -> get_document safe? No SQL but NoSQL? Prompt injection in judge prompts (prompts/judge_prompts.md), role_to_model untrusted?
4. **Insecure Design:** MAX_ACTIVE_BATTLES DoS gate, timeout_seconds max 3600 enforced? sandbox_launcher stop_sandbox on cancel?
5. **Security Misconfig:** CORS allow_origins explicit + regex vercel.app, but missing https enforcement? modal_entry.py exposes internal_router?
6. **Vulnerable Components:** pyproject.toml FastAPI, Appwrite SDK versions, npm audit in frontend
7. **Auth Failures:** get_current_user JWT verify, refreshJwt interval leak, Appwrite JWT vs session, logout clears both storages?
8. **Data Integrity:** event_bus publish without signature, durable load sorted by created_at+event_id stable merge, EXECUTOR_RESULT json parse
9. **Logging/Monitoring:** No secrets in logs? redact.py sanitize_artifact covers API keys, tokens? event_bus logging?
10. **SSRF:** provider base_url user-controlled -> providerHealth POST can SSRF? Check health endpoint validation (allowlist hosts?)

### Step 2 - Sandbox Escape Tests (from advanced-builder evals)

- `eval-tool-escape.md`: attempt TOOL read path=../../etc/passwd, TOOL ls path=/, TOOL write path with .. — must error "ERROR: ..."
- Timeout kill: TOOL run with infinite loop → must SIGKILL pg after 15s, not hang runner
- Gate: instantiate executor without ARENA_IN_SANDBOX=1 → must RuntimeError
- 50KB cap: run large output → [TRUNCATED]
- Redact: artifact containing api_key, OPENAI_API_KEY, Bearer token → sanitized

### Step 3 - Frontend Key Safety

- `lib/api.ts` Authorization header Bearer only, no api key in URL
- `pages/Providers.tsx` — never logs raw key, shows masked only, health check uses POST with body not GET
- `localStorage` arena_jwt: XSS mitigation — check index.html CSP? No script injection in CodePane pre tag (white-space pre-wrap safe, but artifact is code not HTML — never use dangerouslySetInnerHTML)
- Verifiable: `grep -R "dangerouslySetInnerHTML" frontend/src`

### Step 4 - Report & Harden

Produce report per finding:

```
[CRITICAL] Sandbox _resolve bypass
Location: sandbox/executors/advanced_executor.py:_resolve
Evidence: allows .. via normalized path
Fix: if ".." in Path(parts): raise ValueError("ERROR: path traversal")
Test: pytest test_tool_escape
```

Run hardening scripts:

- `scripts/harden_crypto.py` — checks ENCRYPTION_KEY env exists, length, rotation hint
- `scripts/generate_security_report.py` → `reports/security-audit.html`

## Resources

- `references/owasp-arena.md` — OWASP mapped to arena files/lines
- `references/sandbox-gates.md` — ARENA_IN_SANDBOX, ToolSession, Popen killpg pattern
- `references/secrets-checklist.md` — what must never be logged commited
- `scripts/security_scan.py` — deterministic grep + AST audit
- `references/redact-policy.md` — sanitize_artifact rules

## Validation

- `cd backend && pytest tests/test_crypto.py tests/test_redact.py tests/test_auth.py -q`
- `cd frontend && pnpm audit --audit-level=high` (if allowed)
- Manual: try SSRF via Providers health with base_url=http://169.254.169.254

## Example

User: "Audit security of arena-work before prod"
→ Run security_scan.py, check crypto.py, battles.py _get_owned, event_bus ordering, frontend CodePane rendering, produce HTML report, list fixes with severity, run tests.
