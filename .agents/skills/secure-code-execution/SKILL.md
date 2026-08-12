---
name: secure-code-execution
description: >
  Harden systems that execute untrusted or model-generated code. TRIGGER for sandbox
  security, container isolation, resource limits, network restrictions, filesystem
  boundaries, secret handling, subprocess policies, multi-tenant execution, or code
  runner threat modeling. Use for defensive architecture and safe execution controls.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: application-security
  tags: "sandbox-security,code-execution,isolation,containers,secrets,multi-tenant"
---

# Secure Code Execution

Treat all model-generated and user-supplied code as untrusted.

## Security Defaults

1. Run untrusted code outside the application process.
2. Use a dedicated low-privilege identity and isolated runtime per tenant/execution boundary.
3. Deny network access by default; allowlist only destinations required by the product.
4. Provide a minimal filesystem. Avoid host filesystem mounts and Docker socket access.
5. Use read-only base images/filesystems where practical with a small writable workspace.
6. Enforce CPU, memory, process-count, disk, open-file, output-size, and wall-clock limits.
7. Kill the entire process tree on timeout or cancellation.
8. Drop unnecessary Linux capabilities and use the strongest practical syscall/profile isolation supplied by the runtime platform.
9. Never place platform credentials, API keys, cloud metadata credentials, or database secrets in the untrusted process environment unless the execution explicitly requires a scoped temporary credential.
10. Redact secrets from logs, traces, artifacts, errors, and frontend payloads.

## Multi-Tenant Boundaries

Battle participants must not read another participant's workspace unless the battle format explicitly exposes an approved artifact. Never implement opponent visibility by sharing the underlying writable workspace.

Separate control-plane metadata from execution-plane files. Battle IDs and model IDs are not authorization checks by themselves.

## Network Policy

Prefer no egress for pure coding/tests. When egress is necessary, constrain protocol, destination, and credential scope. Block cloud metadata endpoints and private/internal address ranges unless explicitly required by trusted infrastructure.

## Input and Output Safety

Validate archive extraction paths, filenames, symlinks, working directories, commands, and environment variables. Bound stdout/stderr and artifact size. Do not render raw terminal output as HTML.

## Failure Model

Return safe stable error categories such as startup_failed, policy_denied, timed_out, resource_exhausted, execution_failed, and unavailable. Do not expose host paths, infrastructure secrets, internal stack traces, or control-plane tokens to the executing code or end user.

## Review Checklist

Before shipping, threat-model filesystem escape, network pivoting, credential theft, fork bombs, memory/disk exhaustion, symlink/path traversal, process-tree escape, dependency-install abuse, cross-tenant artifact access, log injection, and stale workspace reuse.
